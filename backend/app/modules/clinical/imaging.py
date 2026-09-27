"""Imaging Studies and Findings (#43, design doc §6.3, §15 Stage 4c): a scan and what its report found. The
impression is kept verbatim. A Finding belongs to one study, never linked across studies, and is attributed to a
Condition only when the report says so. Specialty Modules read studies through `study_summaries`.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import entry
from app.modules.clinical.models import Condition, Finding, ImagingStudy
from app.modules.clinical.schemas import (
    FindingChange, FindingRow, ImagingStudyChange, ImagingStudyRow, NewFinding, NewImagingStudy,
)

STUDY_FACT_KIND = "imaging_study"
FINDING_FACT_KIND = "finding"
STUDY = "imaging_study"
FINDING = "finding"
_FINDING_FIELDS = ("site", "laterality", "description", "size_mm", "suv_max", "is_new", "is_measurable", "condition_id")
_STUDY_FIELDS = ("modality", "body_region", "study_date", "impression", "comparison_date")


class NoSuchCondition(ValueError):
    """A Finding's Condition isn't one of this Patient's."""


def _fields(row: ImagingStudy | Finding, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: entry.audit_value(getattr(row, name)) for name in names}


def _check_condition(db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID | None) -> None:
    if condition_id is None:
        return
    found = db.scalars(
        select(Condition.id).where(Condition.id == condition_id, Condition.practice_id == actor.practice_id, Condition.patient_id == patient_id)
    ).first()
    if found is None:
        raise NoSuchCondition("No such Condition for this Patient.")


def _finding_rows(db: Session, actor: Actor, findings: list[Finding]) -> list[FindingRow]:
    condition_ids = {f.condition_id for f in findings if f.condition_id}
    rows = db.execute(select(Condition.id, Condition.name).where(Condition.id.in_(condition_ids)))
    names = {condition_id: name for condition_id, name in rows}
    entered = entry.entered(db, actor.practice_id, FINDING, (f.id for f in findings))
    return [
        FindingRow(
            id=f.id, site=f.site, laterality=f.laterality, description=f.description, size_mm=f.size_mm, suv_max=f.suv_max,  # type: ignore[arg-type]
            is_new=f.is_new, is_measurable=f.is_measurable, condition_id=f.condition_id,
            condition_name=names.get(f.condition_id) if f.condition_id else None, entered=entered.get(f.id),
        )
        for f in findings
    ]


def _rows(db: Session, actor: Actor, studies: list[ImagingStudy]) -> list[ImagingStudyRow]:
    findings = list(db.scalars(
        select(Finding).where(Finding.imaging_study_id.in_([s.id for s in studies])).order_by(Finding.site.nulls_last(), Finding.description, Finding.id)
    )) if studies else []
    rows = _finding_rows(db, actor, findings)
    by_study: dict[uuid.UUID, list[FindingRow]] = {s.id: [] for s in studies}
    for finding, row in zip(findings, rows, strict=True):
        by_study[finding.imaging_study_id].append(row)
    entered = entry.entered(db, actor.practice_id, STUDY, (s.id for s in studies))
    return [
        ImagingStudyRow(
            id=s.id, modality=s.modality, body_region=s.body_region, study_date=s.study_date, impression=s.impression,
            comparison_date=s.comparison_date, findings=by_study[s.id], entered=entered.get(s.id),
        )
        for s in studies
    ]


def _add_finding(db: Session, actor: Actor, patient_id: uuid.UUID, study: ImagingStudy, new: NewFinding) -> Finding:
    _check_condition(db, actor, patient_id, new.condition_id)
    finding = Finding(imaging_study_id=study.id, patient_id=patient_id, **entry.entered_by(actor), **new.model_dump())
    db.add(finding)
    entry.record_added(db, actor, FINDING, finding, _fields(finding, _FINDING_FIELDS))
    return finding


def _finding(db: Session, actor: Actor, patient_id: uuid.UUID, study_id: uuid.UUID, finding_id: uuid.UUID) -> Finding:
    finding = entry.live_row(db, actor, Finding, patient_id, finding_id)
    if finding.imaging_study_id != study_id:
        raise entry.RecordNotFound()
    return finding


def imaging_studies(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[ImagingStudyRow]:
    """Most recent first, each with its Findings by site."""
    entry.require_view(db, actor, patient_id)
    found = db.scalars(
        select(ImagingStudy)
        .where(ImagingStudy.practice_id == actor.practice_id, ImagingStudy.patient_id == patient_id)
        .order_by(ImagingStudy.study_date.desc(), ImagingStudy.created_at.desc())
    )
    return _rows(db, actor, list(found))


@dataclass(frozen=True)
class StudySummary:
    """A study as Specialty Modules see it (their own access checked first)."""

    id: uuid.UUID
    modality: str
    study_date: date


def study_summaries(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> dict[uuid.UUID, StudySummary]:
    """For Specialty Modules: each live study of the Patient, by id."""
    rows = db.execute(
        select(ImagingStudy.id, ImagingStudy.modality, ImagingStudy.study_date)
        .where(ImagingStudy.practice_id == practice_id, ImagingStudy.patient_id == patient_id)
    )
    return {study_id: StudySummary(study_id, modality, study_date) for study_id, modality, study_date in rows}


def add_study(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewImagingStudy) -> ImagingStudyRow:
    """The study and its Findings: one Verification each, in one save."""
    entry.require_entry(db, actor, patient_id, STUDY_FACT_KIND)
    if new.findings:
        entry.require_entry(db, actor, patient_id, FINDING_FACT_KIND)
    study = ImagingStudy(patient_id=patient_id, **entry.entered_by(actor), **new.model_dump(exclude={"findings"}))
    db.add(study)
    entry.record_added(db, actor, STUDY, study, _fields(study, _STUDY_FIELDS))
    for finding in new.findings:
        _add_finding(db, actor, patient_id, study, finding)
    [row] = _rows(db, actor, [study])
    return row


def change_study(db: Session, actor: Actor, patient_id: uuid.UUID, study_id: uuid.UUID, change: ImagingStudyChange) -> ImagingStudyRow:
    entry.require_entry(db, actor, patient_id, STUDY_FACT_KIND)
    study = entry.live_row(db, actor, ImagingStudy, patient_id, study_id)
    entry.correct(db, actor, STUDY, study, _fields(study, _STUDY_FIELDS), change, change.reason, required=("modality", "study_date"))
    [row] = _rows(db, actor, [study])
    return row


def remove_study(db: Session, actor: Actor, patient_id: uuid.UUID, study_id: uuid.UUID, reason: str) -> None:
    """Its Findings go with it."""
    entry.require_entry(db, actor, patient_id, STUDY_FACT_KIND)
    study = entry.live_row(db, actor, ImagingStudy, patient_id, study_id)
    for finding in db.scalars(select(Finding).where(Finding.imaging_study_id == study.id)):
        audit.soft_delete(db, actor, finding, subject_table=FINDING, reason=reason, before=_fields(finding, _FINDING_FIELDS))
    audit.soft_delete(db, actor, study, subject_table=STUDY, reason=reason, before=_fields(study, _STUDY_FIELDS))


def add_finding(db: Session, actor: Actor, patient_id: uuid.UUID, study_id: uuid.UUID, new: NewFinding) -> FindingRow:
    entry.require_entry(db, actor, patient_id, FINDING_FACT_KIND)
    study = entry.live_row(db, actor, ImagingStudy, patient_id, study_id)
    [row] = _finding_rows(db, actor, [_add_finding(db, actor, patient_id, study, new)])
    return row


def change_finding(
    db: Session, actor: Actor, patient_id: uuid.UUID, study_id: uuid.UUID, finding_id: uuid.UUID, change: FindingChange
) -> FindingRow:
    entry.require_entry(db, actor, patient_id, FINDING_FACT_KIND)
    finding = _finding(db, actor, patient_id, study_id, finding_id)
    _check_condition(db, actor, patient_id, change.condition_id)
    entry.correct(db, actor, FINDING, finding, _fields(finding, _FINDING_FIELDS), change, change.reason, required=("description",))
    [row] = _finding_rows(db, actor, [finding])
    return row


def remove_finding(db: Session, actor: Actor, patient_id: uuid.UUID, study_id: uuid.UUID, finding_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, FINDING_FACT_KIND)
    finding = _finding(db, actor, patient_id, study_id, finding_id)
    audit.soft_delete(db, actor, finding, subject_table=FINDING, reason=reason, before=_fields(finding, _FINDING_FIELDS))
