"""Line of Therapy (#40, design doc §6.3, CONTEXT.md): the number given only to a Cancer Diagnosis's palliative
systemic Treatment Courses. **Derived** by start date: each course is the line after the one before it. A
clinician may **override** a course's line with a reason (e.g. maintenance or a re-challenge that isn't a new
line); later courses count on from it. `oncology_course_detail.line_of_therapy` holds only overrides.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import conditions, entry
from app.modules.clinical.treatment_courses import CourseSummary, course_summaries
from app.specialties.oncology import access
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.models import CancerDiagnosis, OncologyCourseDetail
from app.specialties.oncology.schemas import LineOfTherapy, LineOverride

OVERRIDE_FACT_KIND = "line_of_therapy_override"
SUBJECT = "oncology_course_detail"


class NotAPalliativeSystemicCourse(ValueError):
    """Only palliative systemic courses have a Line of Therapy."""


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _counts(course: CourseSummary) -> bool:
    return course.modality == "systemic" and course.intent == "palliative"


def _overrides(db: Session, practice_id: uuid.UUID, course_ids: list[uuid.UUID]) -> dict[uuid.UUID, OncologyCourseDetail]:
    details = db.scalars(
        select(OncologyCourseDetail).where(
            OncologyCourseDetail.practice_id == practice_id, OncologyCourseDetail.treatment_course_id.in_(course_ids),
            OncologyCourseDetail.line_of_therapy.is_not(None),
        )
    )
    return {d.treatment_course_id: d for d in details}


def _when(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def derive(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[LineOfTherapy]:
    """The lines, for any view (access checked by the caller)."""
    names = conditions.extended_conditions(db, practice_id, patient_id, MODULE_KEY)
    diagnoses = {d.condition_id: d.id for d in db.scalars(select(CancerDiagnosis).where(CancerDiagnosis.condition_id.in_(names)))}
    courses = [c for c in course_summaries(db, practice_id, patient_id) if c.condition_id in diagnoses and _counts(c)]
    overrides = _overrides(db, practice_id, [c.id for c in courses])
    reasons = {
        course_id: next((h.reason for h in audit.history(db, practice_id, SUBJECT, detail.id) if h.reason), "")
        for course_id, detail in overrides.items()
    }
    found, previous = [], {condition: 0 for condition in diagnoses}
    positions = dict(previous)
    for course in courses:  # earliest start first
        positions[course.condition_id] += 1
        overridden = course.id in overrides
        line = (overrides[course.id].line_of_therapy or 0) if overridden else previous[course.condition_id] + 1
        previous[course.condition_id] = line
        explanation = (
            f"{ordinal(line)} line, set by a clinician: {reasons[course.id]}" if overridden
            else f"{ordinal(line)} line: {ordinal(positions[course.condition_id])} palliative systemic course of {names[course.condition_id]}"
            + (f", started {_when(course.start_date)}" if course.start_date else "")
        )
        found.append(LineOfTherapy(
            treatment_course_id=course.id, cancer_diagnosis_id=diagnoses[course.condition_id], line=line, overridden=overridden,
            explanation=explanation,
        ))
    return found


def lines_of_therapy(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[LineOfTherapy]:
    """Every palliative systemic course of the Patient's Cancer Diagnoses, with its line and why."""
    access.require_view(db, actor, patient_id)
    return derive(db, actor.practice_id, patient_id)


def override(db: Session, actor: Actor, patient_id: uuid.UUID, course_id: uuid.UUID, change: LineOverride) -> list[LineOfTherapy]:
    access.require_entry(db, actor, patient_id, OVERRIDE_FACT_KIND)
    course = next((c for c in course_summaries(db, actor.practice_id, patient_id) if c.id == course_id), None)
    if course is None:
        raise entry.RecordNotFound()
    if not _counts(course):
        raise NotAPalliativeSystemicCourse("Only a palliative systemic course has a Line of Therapy.")
    detail = db.scalars(
        select(OncologyCourseDetail).where(OncologyCourseDetail.practice_id == actor.practice_id, OncologyCourseDetail.treatment_course_id == course.id)
    ).one_or_none()
    before = detail.line_of_therapy if detail else None
    if before != change.line:
        if detail is None:
            detail = OncologyCourseDetail(treatment_course_id=course.id, **entry.entered_by(actor))
            db.add(detail)
        detail.line_of_therapy = change.line
        db.flush()
        audit.record_verification(
            db, actor, subject_table=SUBJECT, subject_id=detail.id, action="override",
            before={"line": before}, after={"line": change.line}, reason=change.reason,
        )
        db.flush()
    return lines_of_therapy(db, actor, patient_id)
