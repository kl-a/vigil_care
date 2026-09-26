"""Conditions (#35, design doc §6.3): any diagnosed condition a Patient has or has had, entered by hand.

The first Clinical Record kind built on `entry` (the pattern the rest of Stage 4 follows). A Specialty Module
may extend a Condition (Oncology: a Cancer Diagnosis); the Condition itself is Core and always visible.
"""

import uuid
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.changes import blank_to_none
from app.core.permissions import NotAllowed
from app.modules.clinical import entry
from app.modules.clinical.models import Condition
from app.modules.clinical.schemas import ConditionChange, ConditionRow, ConditionStatus, NewCondition

# Its fact kind in Verification Rights, and its table as a Verification's subject: the same name, two roles.
FACT_KIND = "condition"
SUBJECT = "condition"


def _fields(condition: Condition) -> dict[str, Any]:
    """The Condition as a Verification records it (dates as text)."""
    return {
        "name": condition.name,
        "status": condition.status,
        "onset_date": condition.onset_date.isoformat() if condition.onset_date else None,
        "notes": condition.notes,
    }


def _rows(db: Session, actor: Actor, conditions: list[Condition]) -> list[ConditionRow]:
    entered = entry.entered(db, actor.practice_id, SUBJECT, (c.id for c in conditions))
    return [
        ConditionRow(
            id=c.id, name=c.name, status=cast(ConditionStatus, c.status), onset_date=c.onset_date, notes=c.notes,
            extended_by_module=c.extended_by_module, entered=entered.get(c.id),
        )
        for c in conditions
    ]


def extended_conditions(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID, module_key: str) -> dict[uuid.UUID, str]:
    """For Specialty Modules (no actor: the module's own view has checked access): the Patient's live Conditions
    a module extends, by id, with their names."""
    rows = db.execute(
        select(Condition.id, Condition.name).where(
            Condition.practice_id == practice_id, Condition.patient_id == patient_id, Condition.extended_by_module == module_key
        )
    )
    return {condition_id: name for condition_id, name in rows}


def conditions(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[ConditionRow]:
    """Active first, then resolved; each in the order entered."""
    entry.require_view(db, actor, patient_id)
    found = db.scalars(
        select(Condition)
        .where(Condition.practice_id == actor.practice_id, Condition.patient_id == patient_id)
        .order_by(Condition.status != "active", Condition.created_at, Condition.id)
    )
    return _rows(db, actor, list(found))


def add_condition(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewCondition) -> ConditionRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    condition = Condition(patient_id=patient_id, **entry.entered_by(actor), **blank_to_none(new.model_dump()))
    db.add(condition)
    entry.record_added(db, actor, SUBJECT, condition, _fields(condition))
    [row] = _rows(db, actor, [condition])
    return row


def _not_extended(condition: Condition) -> None:
    """A Condition a Specialty Module extends is changed through that module, never from the Core, which would
    bypass the module's rights."""
    if condition.extended_by_module:
        raise NotAllowed("This Condition is recorded through a Specialty Module; change it there.")


def create_extended(
    db: Session, actor: Actor, patient_id: uuid.UUID, module_key: str, name: str
) -> Condition:
    """For Specialty Modules, which check their own rights first: a Condition the module extends, signed off."""
    condition = Condition(patient_id=patient_id, name=name, extended_by_module=module_key, **entry.entered_by(actor))
    db.add(condition)
    entry.record_added(db, actor, SUBJECT, condition, _fields(condition))
    return condition


def _extended(db: Session, actor: Actor, condition_id: uuid.UUID) -> Condition:
    """A live Condition of the actor's Practice that a module extends, or RecordNotFound."""
    condition = db.scalars(
        select(Condition).where(
            Condition.id == condition_id, Condition.practice_id == actor.practice_id, Condition.extended_by_module.is_not(None)
        )
    ).one_or_none()
    if condition is None:
        raise entry.RecordNotFound()
    return condition


def rename_extended(db: Session, actor: Actor, condition_id: uuid.UUID, name: str, reason: str) -> None:
    """For Specialty Modules: correct the name of a Condition the module extends (one Verification, with why)."""
    condition = _extended(db, actor, condition_id)
    if name != condition.name:
        before = _fields(condition)
        condition.name = name
        audit.record_verification(
            db, actor, subject_table=SUBJECT, subject_id=condition.id, action="edit",
            before={"name": before["name"]}, after={"name": name}, reason=reason,
        )
        db.flush()


def remove_extended(db: Session, actor: Actor, condition_id: uuid.UUID, reason: str) -> None:
    """For Specialty Modules: remove a Condition along with the module's extension of it."""
    condition = _extended(db, actor, condition_id)
    audit.soft_delete(db, actor, condition, subject_table=SUBJECT, reason=reason, before=_fields(condition))


def change_condition(
    db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID, change: ConditionChange
) -> ConditionRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    condition = entry.live_row(db, actor, Condition, patient_id, condition_id)
    _not_extended(condition)
    entry.correct(db, actor, SUBJECT, condition, _fields(condition), change, change.reason, required=("name", "status"))
    [row] = _rows(db, actor, [condition])
    return row


def remove_condition(db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    condition = entry.live_row(db, actor, Condition, patient_id, condition_id)
    _not_extended(condition)
    audit.soft_delete(db, actor, condition, subject_table=SUBJECT, reason=reason, before=_fields(condition))
