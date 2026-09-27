"""Biomarkers and Differing Biomarker Results (#38, design doc §6.3, §15 Stage 4a).

Every result of a Cancer Diagnosis is kept, **never overwritten**: a wrong one is removed with a reason and
entered again. The latest per Biomarker and variant (by collection date) is current.

**Differing Biomarker Results** is a deterministic rule, no LLM and no knowledge base: results of the same
Biomarker `name` and `variant` on one Cancer Diagnosis whose recorded `result` categories aren't all the same
(compared ignoring case and spacing, nothing more: no thresholds, no numbers). Vigil only says "Results differ";
it never says why or what to do (TGA decision-support line, design doc §1).
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import entry
from app.specialties.oncology import access
from app.specialties.oncology.models import Biomarker, CancerDiagnosis
from app.specialties.oncology.schemas import BiomarkerChip, BiomarkerMove, BiomarkerRow, NewBiomarker

FACT_KIND = "biomarker"
SUBJECT = "biomarker"
# Moving a result to another primary is a Cancer Diagnosis decision: clinicians only (§6.4 row 4).
MOVE_FACT_KIND = "cancer_diagnosis"
FIELDS = tuple(NewBiomarker.model_fields)


def _key(biomarker: Biomarker) -> tuple[str, str]:
    """Which results are "the same Biomarker": name and variant, ignoring case and spacing."""
    return (" ".join(biomarker.name.split()).casefold(), " ".join((biomarker.variant or "").split()).casefold())


def _category(result: str | None) -> str | None:
    return " ".join(result.split()).casefold() if result else None


def _judge(biomarkers: Iterable[Biomarker]) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
    """(current ids, ids whose Biomarker and variant has differing results)."""
    groups: dict[tuple[uuid.UUID, tuple[str, str]], list[Biomarker]] = defaultdict(list)
    for biomarker in biomarkers:
        groups[(biomarker.cancer_diagnosis_id, _key(biomarker))].append(biomarker)
    current: set[uuid.UUID] = set()
    differing: set[uuid.UUID] = set()
    for group in groups.values():
        latest = max(group, key=lambda b: (b.collected_on is not None, b.collected_on, b.created_at))
        current.add(latest.id)
        if len({c for b in group if (c := _category(b.result))}) > 1:
            differing.update(b.id for b in group)
    return current, differing


def _all_of(db: Session, practice_id: uuid.UUID, diagnosis_ids: Iterable[uuid.UUID]) -> list[Biomarker]:
    return list(db.scalars(
        select(Biomarker)
        .where(Biomarker.practice_id == practice_id, Biomarker.cancer_diagnosis_id.in_(set(diagnosis_ids)))
        .order_by(Biomarker.collected_on.desc().nulls_last(), Biomarker.created_at.desc())
    ))


def current_chips(db: Session, practice_id: uuid.UUID, diagnosis_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[BiomarkerChip]]:
    """Each Cancer Diagnosis's current Biomarkers, A–Z, flagged where results differ."""
    biomarkers = _all_of(db, practice_id, diagnosis_ids)
    current, differing = _judge(biomarkers)
    chips: dict[uuid.UUID, list[BiomarkerChip]] = defaultdict(list)
    for b in sorted((b for b in biomarkers if b.id in current), key=_key):
        chips[b.cancer_diagnosis_id].append(BiomarkerChip(
            name=b.name, variant=b.variant, result=b.result, value_num=b.value_num, value_unit=b.value_unit, differs=b.id in differing,
        ))
    return chips


def _fields(biomarker: Biomarker) -> dict[str, Any]:
    return {field: entry.audit_value(getattr(biomarker, field)) for field in FIELDS}


def _rows(db: Session, actor: Actor, biomarkers: list[Biomarker]) -> list[BiomarkerRow]:
    current, differing = _judge(biomarkers)
    entered = entry.entered(db, actor.practice_id, SUBJECT, (b.id for b in biomarkers))
    return [
        BiomarkerRow(
            id=b.id, current=b.id in current, differs=b.id in differing, entered=entered.get(b.id),
            **{field: getattr(b, field) for field in FIELDS},
        )
        for b in biomarkers
    ]


def _live(db: Session, actor: Actor, diagnosis: CancerDiagnosis, biomarker_id: uuid.UUID) -> Biomarker:
    biomarker = db.scalars(
        select(Biomarker).where(
            Biomarker.id == biomarker_id, Biomarker.practice_id == actor.practice_id, Biomarker.cancer_diagnosis_id == diagnosis.id
        )
    ).one_or_none()
    if biomarker is None:
        raise entry.RecordNotFound()
    return biomarker


def biomarkers(db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID) -> list[BiomarkerRow]:
    """The Cancer Diagnosis's full history, newest first."""
    access.require_view(db, actor, patient_id)
    diagnosis = access.diagnosis_of(db, actor, patient_id, diagnosis_id)
    return _rows(db, actor, _all_of(db, actor.practice_id, [diagnosis.id]))


def add_biomarker(db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID, new: NewBiomarker) -> BiomarkerRow:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    diagnosis = access.diagnosis_of(db, actor, patient_id, diagnosis_id)
    biomarker = Biomarker(cancer_diagnosis_id=diagnosis.id, **entry.entered_by(actor), **new.model_dump())
    db.add(biomarker)
    entry.record_added(db, actor, SUBJECT, biomarker, _fields(biomarker))
    rows = _rows(db, actor, _all_of(db, actor.practice_id, [diagnosis.id]))
    return next(row for row in rows if row.id == biomarker.id)


def remove_biomarker(db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID, biomarker_id: uuid.UUID, reason: str) -> None:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    biomarker = _live(db, actor, access.diagnosis_of(db, actor, patient_id, diagnosis_id), biomarker_id)
    audit.soft_delete(db, actor, biomarker, subject_table=SUBJECT, reason=reason, before=_fields(biomarker))


def move_biomarker(
    db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID, biomarker_id: uuid.UUID, move: BiomarkerMove
) -> BiomarkerRow:
    """To another of the Patient's Cancer Diagnoses, e.g. when a differing result turns out to be a new primary."""
    access.require_entry(db, actor, patient_id, MOVE_FACT_KIND)
    biomarker = _live(db, actor, access.diagnosis_of(db, actor, patient_id, diagnosis_id), biomarker_id)
    target = access.diagnosis_of(db, actor, patient_id, move.cancer_diagnosis_id)
    if target.id != biomarker.cancer_diagnosis_id:
        audit.record_verification(
            db, actor, subject_table=SUBJECT, subject_id=biomarker.id, action="move",
            before={"cancer_diagnosis_id": str(biomarker.cancer_diagnosis_id)}, after={"cancer_diagnosis_id": str(target.id)},
            reason=move.reason,
        )
        biomarker.cancer_diagnosis_id = target.id
        db.flush()
    rows = _rows(db, actor, _all_of(db, actor.practice_id, [target.id]))
    return next(row for row in rows if row.id == biomarker.id)


def plain(chip: BiomarkerChip) -> str:
    """A current result in plain words, e.g. "HER2 negative (0 IHC score) (results differ)"."""
    value = f"({chip.value_num}{' ' + chip.value_unit if chip.value_unit else ''})" if chip.value_num is not None else None
    words = " ".join(part for part in (chip.name, chip.variant, chip.result, value) if part)
    return words + (" (results differ)" if chip.differs else "")
