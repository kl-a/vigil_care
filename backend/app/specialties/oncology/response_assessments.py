"""Response Assessments and each course's best response (#43, design doc §6.3–6.4, §15 Stage 4c).

- A **Response Assessment** says which way a Cancer Diagnosis is going (responding, stable, progressing), as a
  radiology report states it (clinicians and trial coordinators) or as a clinician judges it (clinicians only),
  optionally from an Imaging Study. "Not sure which" Cancer Diagnosis is allowed: it's recorded unattributed and only a
  clinician attributes it later (§6.4 row 4; its Open Item comes in Stage 5).
- A clinician **overrides** one with their own direction and a reason: a new assessment (source `clinician`) that
  counts instead of it.
- A Treatment Course's **best response** is derived, never stored: the best direction (responding > stable >
  progressing, the earliest on a tie) among its Cancer Diagnosis's assessments dated during the course, linked
  to the assessment it came from. Surgery has none.
"""

import uuid
from collections.abc import Callable
from datetime import date
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import conditions, entry
from app.modules.clinical.imaging import StudySummary, study_summaries
from app.modules.clinical.treatment_courses import CourseSummary, course_summaries
from app.specialties.oncology import access
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.models import CancerDiagnosis, ResponseAssessment
from app.specialties.oncology.schemas import (
    Attribution, BestResponse, Direction, NewResponseAssessment, ResponseAssessmentRow, ResponseOverride, ResponseSource,
)

FACT_KIND = "response_assessment"
# A clinician's own assessment, an override, and attributing an unattributed one (§6.4 row 4).
CLINICIAN_FACT_KIND = "response_assessment_override"
SUBJECT = "response_assessment"
RANK: dict[str, int] = {"responding": 0, "stable": 1, "progressing": 2}
SOURCE_WORDS = {"radiology_report": "radiology report", "clinician": "clinician"}


class InvalidAssessment(ValueError):
    """Its Imaging Study isn't one of this Patient's."""


class AlreadyDone(ValueError):
    """Attributing one already attributed, or overriding one already overridden."""


def _fields(a: ResponseAssessment) -> dict[str, Any]:
    return {
        "cancer_diagnosis_id": entry.audit_value(a.cancer_diagnosis_id), "assessed_on": entry.audit_value(a.assessed_on),
        "direction": a.direction, "source": a.source, "imaging_study_id": entry.audit_value(a.imaging_study_id),
        "overrides_id": entry.audit_value(a.overrides_id),
    }


def _diagnosis_names(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """Each of the Patient's Cancer Diagnoses, by the name of the Condition it extends."""
    names = conditions.extended_conditions(db, practice_id, patient_id, MODULE_KEY)
    return {d.id: names[d.condition_id] for d in db.scalars(select(CancerDiagnosis).where(CancerDiagnosis.condition_id.in_(names)))}


def _all(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[ResponseAssessment]:
    """Live ones, newest first."""
    return list(db.scalars(
        select(ResponseAssessment)
        .where(ResponseAssessment.practice_id == practice_id, ResponseAssessment.patient_id == patient_id)
        .order_by(ResponseAssessment.assessed_on.desc(), ResponseAssessment.created_at.desc())
    ))


def _overridden_by(assessments: list[ResponseAssessment]) -> dict[uuid.UUID, uuid.UUID]:
    return {a.overrides_id: a.id for a in assessments if a.overrides_id}


def _counted(assessments: list[ResponseAssessment]) -> list[ResponseAssessment]:
    """The ones that count: not overridden."""
    overridden = _overridden_by(assessments)
    return [a for a in assessments if a.id not in overridden]


def _rows(db: Session, actor: Actor, patient_id: uuid.UUID, shown: list[ResponseAssessment]) -> list[ResponseAssessmentRow]:
    names = _diagnosis_names(db, actor.practice_id, patient_id)
    overridden = _overridden_by(_all(db, actor.practice_id, patient_id))
    entered = entry.entered(db, actor.practice_id, SUBJECT, (a.id for a in shown))
    return [
        ResponseAssessmentRow(
            id=a.id, cancer_diagnosis_id=a.cancer_diagnosis_id, cancer_diagnosis_name=names.get(a.cancer_diagnosis_id) if a.cancer_diagnosis_id else None,
            assessed_on=a.assessed_on, direction=cast(Direction, a.direction), source=cast(ResponseSource, a.source),
            imaging_study_id=a.imaging_study_id, overrides_id=a.overrides_id, overridden_by_id=overridden.get(a.id),
            override_reason=_override_reason(db, actor, a) if a.overrides_id else None, entered=entered.get(a.id),
        )
        for a in shown
    ]


def _override_reason(db: Session, actor: Actor, assessment: ResponseAssessment) -> str | None:
    return next((h.reason for h in audit.history(db, actor.practice_id, SUBJECT, assessment.id) if h.action == "override"), None)


def _one(db: Session, actor: Actor, patient_id: uuid.UUID, assessment: ResponseAssessment) -> ResponseAssessmentRow:
    db.flush()
    [row] = _rows(db, actor, patient_id, [assessment])
    return row


def response_assessments(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[ResponseAssessmentRow]:
    """Every one, overridden ones included (marked), newest first."""
    access.require_view(db, actor, patient_id)
    return _rows(db, actor, patient_id, _all(db, actor.practice_id, patient_id))


def record(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewResponseAssessment) -> ResponseAssessmentRow:
    access.require_entry(db, actor, patient_id, CLINICIAN_FACT_KIND if new.source == "clinician" else FACT_KIND)
    if new.cancer_diagnosis_id:
        access.diagnosis_of(db, actor, patient_id, new.cancer_diagnosis_id)
    if new.imaging_study_id and new.imaging_study_id not in study_summaries(db, actor.practice_id, patient_id):
        raise InvalidAssessment("No such Imaging Study for this Patient.")
    assessment = ResponseAssessment(patient_id=patient_id, **entry.entered_by(actor), **new.model_dump())
    db.add(assessment)
    entry.record_added(db, actor, SUBJECT, assessment, _fields(assessment))
    return _one(db, actor, patient_id, assessment)


def attribute(db: Session, actor: Actor, patient_id: uuid.UUID, assessment_id: uuid.UUID, attribution: Attribution) -> ResponseAssessmentRow:
    """A clinician says which Cancer Diagnosis an unattributed one is of. A clinician's override of it follows."""
    access.require_entry(db, actor, patient_id, CLINICIAN_FACT_KIND)
    assessment = entry.live_row(db, actor, ResponseAssessment, patient_id, assessment_id)
    if assessment.cancer_diagnosis_id is not None:
        raise AlreadyDone("This Response Assessment is already attributed.")
    diagnosis = access.diagnosis_of(db, actor, patient_id, attribution.cancer_diagnosis_id)
    # An override copies its original's Cancer Diagnosis, so attributing one attributes its override too.
    overrides = [a for a in _all(db, actor.practice_id, patient_id) if a.overrides_id == assessment.id and a.cancer_diagnosis_id is None]
    for row in (assessment, *overrides):
        audit.record_verification(
            db, actor, subject_table=SUBJECT, subject_id=row.id, action="attribute",
            before={"cancer_diagnosis_id": None}, after={"cancer_diagnosis_id": str(diagnosis.id)},
        )
        row.cancer_diagnosis_id = diagnosis.id
    return _one(db, actor, patient_id, assessment)


def override(db: Session, actor: Actor, patient_id: uuid.UUID, assessment_id: uuid.UUID, change: ResponseOverride) -> ResponseAssessmentRow:
    """The clinician's direction counts instead, for the same Cancer Diagnosis, date and scan."""
    access.require_entry(db, actor, patient_id, CLINICIAN_FACT_KIND)
    original = entry.live_row(db, actor, ResponseAssessment, patient_id, assessment_id)
    if original.id in _overridden_by(_all(db, actor.practice_id, patient_id)):
        raise AlreadyDone("This Response Assessment is already overridden; override the clinician's instead.")
    replacement = ResponseAssessment(
        patient_id=patient_id, cancer_diagnosis_id=original.cancer_diagnosis_id, assessed_on=original.assessed_on, direction=change.direction,
        source="clinician", imaging_study_id=original.imaging_study_id, overrides_id=original.id, **entry.entered_by(actor),
    )
    db.add(replacement)
    db.flush()
    audit.record_verification(
        db, actor, subject_table=SUBJECT, subject_id=replacement.id, action="override",
        before={"direction": original.direction, "response_assessment_id": str(original.id)}, after=_fields(replacement), reason=change.reason,
    )
    return _one(db, actor, patient_id, replacement)


def remove(db: Session, actor: Actor, patient_id: uuid.UUID, assessment_id: uuid.UUID, reason: str) -> None:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    assessment = entry.live_row(db, actor, ResponseAssessment, patient_id, assessment_id)
    if assessment.source == "clinician":  # a clinician's own assessment: clinicians only
        access.require_entry(db, actor, patient_id, CLINICIAN_FACT_KIND)
    audit.soft_delete(db, actor, assessment, subject_table=SUBJECT, reason=reason, before=_fields(assessment))


# --- Best response ----------------------------------------------------------------------------------------


def _when(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def _during(course: CourseSummary, day: date) -> bool:
    return course.start_date is not None and course.start_date <= day and (course.end_date is None or day <= course.end_date)


def _scan(study: StudySummary) -> str:
    return f"{study.modality} of {_when(study.study_date)}"


def derive_best(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[BestResponse]:
    """Each course of a Cancer Diagnosis with an assessment during it (access checked by the caller)."""
    names = conditions.extended_conditions(db, practice_id, patient_id, MODULE_KEY)
    diagnoses = {d.condition_id: d.id for d in db.scalars(select(CancerDiagnosis).where(CancerDiagnosis.condition_id.in_(names)))}
    counted = _counted(_all(db, practice_id, patient_id))
    studies = study_summaries(db, practice_id, patient_id)
    found = []
    for course in course_summaries(db, practice_id, patient_id):
        if course.condition_id not in diagnoses or course.modality == "surgery":
            continue
        during = [a for a in counted if a.cancer_diagnosis_id == diagnoses[course.condition_id] and _during(course, a.assessed_on)]
        if not during:
            continue
        best = min(during, key=lambda a: (RANK[a.direction], a.assessed_on))
        study = studies.get(best.imaging_study_id) if best.imaging_study_id else None
        source = f"on {_scan(study)}" if study else f"assessed {_when(best.assessed_on)}"
        found.append(BestResponse(
            treatment_course_id=course.id, direction=cast(Direction, best.direction), response_assessment_id=best.id,
            imaging_study_id=best.imaging_study_id,
            explanation=f"{best.direction.capitalize()}: best response during {course.regimen_name or course.modality}, {source}",
        ))
    return found


def best_responses(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[BestResponse]:
    access.require_view(db, actor, patient_id)
    return derive_best(db, actor.practice_id, patient_id)


def plain_lines(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID, when: Callable[[date], str]) -> list[str]:
    """For the read-only view: the assessments that count, newest first, then each course's best response. e.g.
    "Breast cancer: responding (radiology report, CT of 14 Aug 2026), 14 Aug 2026"."""
    names = _diagnosis_names(db, practice_id, patient_id)
    studies = study_summaries(db, practice_id, patient_id)
    lines = []
    for a in _counted(_all(db, practice_id, patient_id)):
        study = studies.get(a.imaging_study_id) if a.imaging_study_id else None
        how = SOURCE_WORDS[a.source] + (f", {_scan(study)}" if study else "")
        of = names.get(a.cancer_diagnosis_id, "") if a.cancer_diagnosis_id else "Cancer Diagnosis not yet attributed"
        lines.append(f"{of}: {a.direction} ({how}), {when(a.assessed_on)}")
    return lines + [b.explanation for b in derive_best(db, practice_id, patient_id)]
