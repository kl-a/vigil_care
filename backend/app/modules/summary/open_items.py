"""Open Items (#48, design doc §6.3): derived, never stored, never dismissed. Each clears only when someone acts on
what's behind it. The Core raises **Next Steps coming due**; each active Specialty Module raises its own types
through the module contract (`open_items`), so switching a module off takes its Open Items with it (ADR 0004).
"""

import uuid
from collections.abc import Collection
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.clock import practice_today
from app.core.permissions import require
from app.modules.clinical import entry
from app.modules.clinical.models import NextStep
from app.modules.patients.service import patient_names
from app.modules.registry.registry import installed_modules
from app.modules.registry.service import active_module_keys
from app.modules.summary.schemas import OpenItem, OpenItemAction, Who

# A Next Step becomes an Open Item this many days before it's due (revisit-later #29).
NEXT_STEP_WINDOW = timedelta(days=7)


def _when(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def _next_steps(db: Session, practice_id: uuid.UUID, patient_ids: Collection[uuid.UUID] | None) -> list[OpenItem]:
    today = practice_today()
    query = select(NextStep).where(
        NextStep.practice_id == practice_id, NextStep.done_at.is_(None), NextStep.due_date.is_not(None),
        NextStep.due_date <= today + NEXT_STEP_WINDOW,
    )
    if patient_ids is not None:
        query = query.where(NextStep.patient_id.in_(patient_ids))
    return [
        OpenItem(
            type="next_step", type_label="Next Step", patient_id=step.patient_id, title=step.description,
            detail=f"Overdue since {_when(step.due_date)}" if step.due_date < today else f"Due {_when(step.due_date)}",
            dated=step.due_date, who="staff", icon="calendar", subject_table="next_step", subject_id=step.id, open_tab="clinical-data",
            actions=[OpenItemAction(label="Mark done", path=f"/patients/{step.patient_id}/next-steps/{step.id}/done")],
        )
        for step in db.scalars(query) if step.due_date
    ]


def derive(db: Session, practice_id: uuid.UUID, patient_ids: Collection[uuid.UUID] | None) -> list[OpenItem]:
    """The Core's and the active modules' Open Items, soonest first (access checked by the caller)."""
    found = _next_steps(db, practice_id, patient_ids)
    active = set(active_module_keys(db, practice_id))
    for key, module in installed_modules().items():
        if key in active and module.open_items is not None:
            found += module.open_items(db, practice_id, patient_ids)
    return sorted(found, key=lambda item: (item.dated is None, item.dated or date.min, item.type, item.title))


def patient_open_items(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[OpenItem]:
    entry.require_view(db, actor, patient_id)
    return derive(db, actor.practice_id, {patient_id})


def practice_open_items(db: Session, actor: Actor, kind: str | None = None, who: Who | None = None) -> list[OpenItem]:
    """The Practice's queue (the Dashboard), each named with its Patient; never another Practice's."""
    require(actor.job_title, "view_patient_data")
    found = [i for i in derive(db, actor.practice_id, None) if (kind is None or i.type == kind) and (who is None or i.who == who)]
    names = patient_names(db, actor.practice_id, {i.patient_id for i in found})
    # A removed Patient's items go with them.
    return [i.model_copy(update={"patient_name": names[i.patient_id]}) for i in found if i.patient_id in names]
