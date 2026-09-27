"""Treatment Courses (#40, design doc §6.3, §15 Stage 4b): any course of treatment for one of the Patient's
Conditions (Core): systemic with its Regimen (planned drugs and doses), surgery or radiation. A course is ongoing
until a User records that it ended. Specialty Modules add their own view of a course through `course_summaries`.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import entry
from app.modules.clinical.models import Condition, TreatmentCourse
from app.modules.clinical.schemas import (
    Intent, Modality, NewTreatmentCourse, RegimenDrug, TreatmentCourseChange, TreatmentCourseRow,
)

FACT_KIND = "treatment_course"
SUBJECT = "treatment_course"


class NoSuchCondition(ValueError):
    """The course's Condition isn't one of this Patient's."""


class InvalidCourse(ValueError):
    """The change would leave the course inconsistent (e.g. ending before it starts)."""


def _drugs(course: TreatmentCourse) -> list[dict[str, Any]]:
    return list((course.regimen_planned or {}).get("drugs", []))


def _fields(course: TreatmentCourse) -> dict[str, Any]:
    """The course as its Verifications record it: the Regimen's drugs as `regimen_drugs`."""
    return {
        "intent": course.intent, "regimen_name": course.regimen_name, "regimen_drugs": _drugs(course),
        "start_date": entry.audit_value(course.start_date), "end_date": entry.audit_value(course.end_date),
        "reason_stopped": course.reason_stopped, "details": course.details,
    }


def _rows(db: Session, actor: Actor, courses: list[TreatmentCourse]) -> list[TreatmentCourseRow]:
    rows = db.execute(select(Condition.id, Condition.name).where(Condition.id.in_({c.condition_id for c in courses})))
    names = {condition_id: name for condition_id, name in rows}
    entered = entry.entered(db, actor.practice_id, SUBJECT, (c.id for c in courses))
    return [
        TreatmentCourseRow(
            id=c.id, condition_id=c.condition_id, condition_name=names.get(c.condition_id, ""), modality=cast(Modality, c.modality),
            intent=cast(Intent | None, c.intent), regimen_name=c.regimen_name, regimen_drugs=[RegimenDrug(**d) for d in _drugs(c)],
            start_date=c.start_date, end_date=c.end_date, ongoing=c.end_date is None, reason_stopped=c.reason_stopped,
            details=c.details, entered=entered.get(c.id),
        )
        for c in courses
    ]


def _patients_condition(db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID) -> None:
    found = db.scalars(
        select(Condition.id).where(Condition.id == condition_id, Condition.practice_id == actor.practice_id, Condition.patient_id == patient_id)
    ).first()
    if found is None:
        raise NoSuchCondition("No such Condition for this Patient.")


def _course(db: Session, actor: Actor, patient_id: uuid.UUID, course_id: uuid.UUID) -> TreatmentCourse:
    """One of the Patient's live courses (its Condition is the Patient's)."""
    course = db.scalars(
        select(TreatmentCourse)
        .join(Condition, Condition.id == TreatmentCourse.condition_id)
        .where(TreatmentCourse.id == course_id, TreatmentCourse.practice_id == actor.practice_id, Condition.patient_id == patient_id)
    ).one_or_none()
    if course is None:
        raise entry.RecordNotFound()
    return course


@dataclass(frozen=True)
class CourseSummary:
    """A course as Specialty Modules see it (their own access checked first)."""

    id: uuid.UUID
    condition_id: uuid.UUID
    modality: str
    intent: str | None
    regimen_name: str | None
    start_date: date | None


def course_summaries(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[CourseSummary]:
    """For Specialty Modules: the Patient's live courses, earliest start first."""
    return [
        CourseSummary(id=c.id, condition_id=c.condition_id, modality=c.modality, intent=c.intent, regimen_name=c.regimen_name, start_date=c.start_date)
        for c in _patient_courses(db, practice_id, patient_id)
    ]


def _patient_courses(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[TreatmentCourse]:
    return list(db.scalars(
        select(TreatmentCourse)
        .join(Condition, Condition.id == TreatmentCourse.condition_id)
        .where(TreatmentCourse.practice_id == practice_id, Condition.patient_id == patient_id)
        .order_by(TreatmentCourse.start_date.asc().nulls_last(), TreatmentCourse.created_at)
    ))


def treatment_courses(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[TreatmentCourseRow]:
    """Most recent start first."""
    entry.require_view(db, actor, patient_id)
    return _rows(db, actor, list(reversed(_patient_courses(db, actor.practice_id, patient_id))))


def add_course(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewTreatmentCourse) -> TreatmentCourseRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    _patients_condition(db, actor, patient_id, new.condition_id)
    values = new.model_dump(exclude={"regimen_drugs", "details"})
    # JSON columns are set only when they have a value: left unset they're SQL NULL, not JSON null (the
    # database allows a Regimen on systemic courses only).
    if new.details is not None:
        values["details"] = new.details
    if new.modality == "systemic":
        values["regimen_planned"] = {"drugs": [d.model_dump() for d in new.regimen_drugs]}
    course = TreatmentCourse(**entry.entered_by(actor), **values)
    db.add(course)
    entry.record_added(db, actor, SUBJECT, course, _fields(course))
    [row] = _rows(db, actor, [course])
    return row


def change_course(db: Session, actor: Actor, patient_id: uuid.UUID, course_id: uuid.UUID, change: TreatmentCourseChange) -> TreatmentCourseRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    course = _course(db, actor, patient_id, course_id)
    if course.modality != "systemic" and (change.regimen_name or change.regimen_drugs):
        raise InvalidCourse("Only a systemic course has a Regimen.")
    # A Specialty Module's record may depend on a course's intent (e.g. a line only on palliative systemic
    # courses, a deferred database check): checked now, in a savepoint, so a clash is a clear refusal.
    try:
        with db.begin_nested():
            db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            entry.correct(db, actor, SUBJECT, course, _fields(course), change, change.reason, exclude=("regimen_drugs",))
    except IntegrityError:
        raise InvalidCourse("Another record depends on this course's intent; change that first.") from None
    if change.regimen_drugs is not None and [d.model_dump() for d in change.regimen_drugs] != _drugs(course):
        before = _drugs(course)
        course.regimen_planned = {"drugs": [d.model_dump() for d in change.regimen_drugs]}
        audit.record_verification(
            db, actor, subject_table=SUBJECT, subject_id=course.id, action="edit",
            before={"regimen_drugs": before}, after={"regimen_drugs": _drugs(course)}, reason=change.reason,
        )
    if course.start_date and course.end_date and course.end_date < course.start_date:
        raise InvalidCourse("A course can't end before it starts.")
    db.flush()
    [row] = _rows(db, actor, [course])
    return row


def remove_course(db: Session, actor: Actor, patient_id: uuid.UUID, course_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    course = _course(db, actor, patient_id, course_id)
    audit.soft_delete(db, actor, course, subject_table=SUBJECT, reason=reason, before=_fields(course))
