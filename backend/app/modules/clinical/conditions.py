"""Conditions (#35, design doc §6.3): any diagnosed condition a Patient has or has had, entered by hand.

The first Clinical Record kind built on `entry` (the pattern the rest of Stage 4 follows). A Specialty Module
may extend a Condition (Oncology: a Cancer Diagnosis); the Condition itself is Core and always visible.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.changes import blank_to_none
from app.modules.clinical import entry
from app.modules.clinical.models import Condition
from app.modules.clinical.schemas import ConditionChange, ConditionRow, NewCondition

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
            id=c.id, name=c.name, status=c.status, onset_date=c.onset_date, notes=c.notes,  # type: ignore[arg-type]
            extended_by_module=c.extended_by_module, entered=entered.get(c.id),
        )
        for c in conditions
    ]


def _condition(db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID) -> Condition:
    condition = db.scalars(
        select(Condition).where(
            Condition.id == condition_id, Condition.patient_id == patient_id, Condition.practice_id == actor.practice_id
        )
    ).one_or_none()
    if condition is None:
        raise entry.RecordNotFound()
    return condition


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


def change_condition(
    db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID, change: ConditionChange
) -> ConditionRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    condition = _condition(db, actor, patient_id, condition_id)
    entry.correct(db, actor, SUBJECT, condition, _fields(condition), change, change.reason, required=("name", "status"))
    [row] = _rows(db, actor, [condition])
    return row


def remove_condition(db: Session, actor: Actor, patient_id: uuid.UUID, condition_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    condition = _condition(db, actor, patient_id, condition_id)
    audit.soft_delete(db, actor, condition, subject_table=SUBJECT, reason=reason, before=_fields(condition))
