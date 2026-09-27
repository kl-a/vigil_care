"""Plan and notes (#45, design doc §6.3, §15 Stage 4c).

- **Management Plan:** the treating clinician's plan, **quoted verbatim** with its author (a Provider) and date.
  Vigil never rewrites it; a new plan is a new row, so earlier ones stay.
- **Clinical Notes** and letters, with author and recipient Providers.
- **Next Steps:** dated items alongside the plan. Any staff member adds them and marks them done (§6.4 row 1);
  they aren't Clinical Record values, so they carry who created them rather than provenance.

Notes and plans follow `entry` (Verification Rights, provenance, a reason per correction).
"""

import uuid
from typing import Any, cast

from sqlalchemy import func, nulls_last, select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.changes import blank_to_none
from app.core.permissions import require
from app.modules.clinical import entry
from app.modules.clinical.models import ClinicalNote, ManagementPlan, NextStep
from app.modules.clinical.schemas import (
    ClinicalNoteChange, ClinicalNoteRow, Done, ManagementPlanChange, ManagementPlanRow, NewClinicalNote,
    NewManagementPlan, NewNextStep, NextStepChange, NextStepKind, NextStepRow, NoteType,
)
from app.modules.accounts.service import display_names
from app.modules.practice.providers import provider_names

PLAN = "management_plan"
NOTE = "clinical_note"
NEXT_STEP = "next_step"


class NoSuchProvider(ValueError):
    """An author or recipient isn't a live Provider in this Practice's directory."""


class AlreadyDone(ValueError):
    """The Next Step is already marked done."""


def _check_providers(db: Session, actor: Actor, *provider_ids: uuid.UUID | None) -> None:
    wanted = {p for p in provider_ids if p is not None}
    if wanted and len(provider_names(db, actor.practice_id, wanted)) != len(wanted):
        raise NoSuchProvider("No such Provider in this Practice.")


def _names(db: Session, actor: Actor, ids: set[uuid.UUID | None]) -> dict[uuid.UUID | None, str]:
    """Providers by name, including removed ones (their notes and plans keep their place). Looking up None
    (no Provider recorded) gives None."""
    found = provider_names(db, actor.practice_id, {i for i in ids if i is not None}, include_removed=True)
    return {provider_id: name for provider_id, name in found.items()}


# --- Management Plan ------------------------------------------------------------------------------------------


def _plan_fields(plan: ManagementPlan) -> dict[str, Any]:
    return {"plan_text": plan.plan_text, "plan_date": entry.audit_value(plan.plan_date), "authored_by_provider_id": entry.audit_value(plan.authored_by_provider_id)}


def _plan_rows(db: Session, actor: Actor, plans: list[ManagementPlan]) -> list[ManagementPlanRow]:
    names = _names(db, actor, {p.authored_by_provider_id for p in plans})
    entered = entry.entered(db, actor.practice_id, PLAN, (p.id for p in plans))
    return [
        ManagementPlanRow(
            id=p.id, plan_text=p.plan_text, plan_date=p.plan_date, authored_by_provider_id=p.authored_by_provider_id,
            author_name=names.get(p.authored_by_provider_id), entered=entered.get(p.id),
        )
        for p in plans
    ]


def management_plans(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[ManagementPlanRow]:
    """Newest first: the first is the current plan, the rest its history."""
    entry.require_view(db, actor, patient_id)
    plans = db.scalars(
        select(ManagementPlan)
        .where(ManagementPlan.practice_id == actor.practice_id, ManagementPlan.patient_id == patient_id)
        .order_by(nulls_last(ManagementPlan.plan_date.desc()), ManagementPlan.created_at.desc())
    )
    return _plan_rows(db, actor, list(plans))


def add_management_plan(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewManagementPlan) -> ManagementPlanRow:
    entry.require_entry(db, actor, patient_id, PLAN)
    _check_providers(db, actor, new.authored_by_provider_id)
    # Verbatim: stored exactly as given.
    plan = ManagementPlan(patient_id=patient_id, **entry.entered_by(actor), **new.model_dump())
    db.add(plan)
    entry.record_added(db, actor, PLAN, plan, _plan_fields(plan))
    [row] = _plan_rows(db, actor, [plan])
    return row


def change_management_plan(
    db: Session, actor: Actor, patient_id: uuid.UUID, plan_id: uuid.UUID, change: ManagementPlanChange
) -> ManagementPlanRow:
    entry.require_entry(db, actor, patient_id, PLAN)
    plan = entry.live_row(db, actor, ManagementPlan, patient_id, plan_id)
    _check_providers(db, actor, change.authored_by_provider_id)
    entry.correct(db, actor, PLAN, plan, _plan_fields(plan), change, change.reason, required=("plan_text",))
    [row] = _plan_rows(db, actor, [plan])
    return row


def remove_management_plan(db: Session, actor: Actor, patient_id: uuid.UUID, plan_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, PLAN)
    plan = entry.live_row(db, actor, ManagementPlan, patient_id, plan_id)
    audit.soft_delete(db, actor, plan, subject_table=PLAN, reason=reason, before=_plan_fields(plan))


# --- Clinical Notes -------------------------------------------------------------------------------------------


def _note_fields(note: ClinicalNote) -> dict[str, Any]:
    return {
        "note_type": note.note_type, "note_date": entry.audit_value(note.note_date), "author_provider_id": entry.audit_value(note.author_provider_id),
        "recipient_provider_id": entry.audit_value(note.recipient_provider_id), "content": note.content_summary,
    }


def _note_rows(db: Session, actor: Actor, notes: list[ClinicalNote]) -> list[ClinicalNoteRow]:
    names = _names(db, actor, {n.author_provider_id for n in notes} | {n.recipient_provider_id for n in notes})
    entered = entry.entered(db, actor.practice_id, NOTE, (n.id for n in notes))
    return [
        ClinicalNoteRow(
            id=n.id, note_type=cast(NoteType, n.note_type), note_date=n.note_date,
            author_provider_id=n.author_provider_id, author_name=names.get(n.author_provider_id),
            recipient_provider_id=n.recipient_provider_id,
            recipient_name=names.get(n.recipient_provider_id),
            content=n.content_summary, entered=entered.get(n.id),
        )
        for n in notes
    ]


def clinical_notes(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[ClinicalNoteRow]:
    """Newest first."""
    entry.require_view(db, actor, patient_id)
    notes = db.scalars(
        select(ClinicalNote)
        .where(ClinicalNote.practice_id == actor.practice_id, ClinicalNote.patient_id == patient_id)
        .order_by(nulls_last(ClinicalNote.note_date.desc()), ClinicalNote.created_at.desc())
    )
    return _note_rows(db, actor, list(notes))


def add_clinical_note(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewClinicalNote) -> ClinicalNoteRow:
    entry.require_entry(db, actor, patient_id, NOTE)
    _check_providers(db, actor, new.author_provider_id, new.recipient_provider_id)
    note = ClinicalNote(patient_id=patient_id, **entry.entered_by(actor), **new.model_dump())
    db.add(note)
    entry.record_added(db, actor, NOTE, note, _note_fields(note))
    [row] = _note_rows(db, actor, [note])
    return row


def change_clinical_note(
    db: Session, actor: Actor, patient_id: uuid.UUID, note_id: uuid.UUID, change: ClinicalNoteChange
) -> ClinicalNoteRow:
    entry.require_entry(db, actor, patient_id, NOTE)
    note = entry.live_row(db, actor, ClinicalNote, patient_id, note_id)
    _check_providers(db, actor, change.author_provider_id, change.recipient_provider_id)
    entry.correct(db, actor, NOTE, note, _note_fields(note), change, change.reason, required=("note_type", "content"))
    [row] = _note_rows(db, actor, [note])
    return row


def remove_clinical_note(db: Session, actor: Actor, patient_id: uuid.UUID, note_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, NOTE)
    note = entry.live_row(db, actor, ClinicalNote, patient_id, note_id)
    audit.soft_delete(db, actor, note, subject_table=NOTE, reason=reason, before=_note_fields(note))


# --- Next Steps -----------------------------------------------------------------------------------------------


def _require_next_steps(db: Session, actor: Actor, patient_id: uuid.UUID) -> None:
    entry.require_view(db, actor, patient_id)
    require(actor.job_title, "manage_next_steps")


def _step_fields(step: NextStep) -> dict[str, Any]:
    return {"kind": step.kind, "description": step.description, "due_date": entry.audit_value(step.due_date)}


def _step_rows(db: Session, actor: Actor, steps: list[NextStep]) -> list[NextStepRow]:
    entered = entry.entered(db, actor.practice_id, NEXT_STEP, (s.id for s in steps))
    done_by = display_names(db, {s.done_by_user_id for s in steps if s.done_by_user_id})
    return [
        NextStepRow(
            id=s.id, kind=cast(NextStepKind, s.kind), description=s.description, due_date=s.due_date,
            entered=entered.get(s.id),
            done=Done(by=done_by.get(s.done_by_user_id, "Unknown User"), at=s.done_at) if s.done_at and s.done_by_user_id else None,
        )
        for s in steps
    ]


def next_steps(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[NextStepRow]:
    """Open ones first, soonest due first; then those done, most recently done first."""
    _require_next_steps(db, actor, patient_id)
    steps = db.scalars(
        select(NextStep)
        .where(NextStep.practice_id == actor.practice_id, NextStep.patient_id == patient_id)
        .order_by(NextStep.done_at.is_not(None), nulls_last(NextStep.due_date.asc()), NextStep.done_at.desc(), NextStep.created_at)
    )
    return _step_rows(db, actor, list(steps))


def add_next_step(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewNextStep) -> NextStepRow:
    _require_next_steps(db, actor, patient_id)
    step = NextStep(patient_id=patient_id, practice_id=actor.practice_id, created_by_user_id=actor.id, **blank_to_none(new.model_dump()))
    db.add(step)
    entry.record_added(db, actor, NEXT_STEP, step, _step_fields(step))
    [row] = _step_rows(db, actor, [step])
    return row


def mark_next_step_done(db: Session, actor: Actor, patient_id: uuid.UUID, step_id: uuid.UUID) -> NextStepRow:
    _require_next_steps(db, actor, patient_id)
    step = entry.live_row(db, actor, NextStep, patient_id, step_id)
    if step.done_at is not None:
        raise AlreadyDone("This Next Step is already done.")
    step.done_at, step.done_by_user_id = func.now(), actor.id
    audit.record_verification(db, actor, subject_table=NEXT_STEP, subject_id=step.id, action="edit", before={"done": False}, after={"done": True})
    db.flush()
    db.refresh(step)
    [row] = _step_rows(db, actor, [step])
    return row


def change_next_step(db: Session, actor: Actor, patient_id: uuid.UUID, step_id: uuid.UUID, change: NextStepChange) -> NextStepRow:
    _require_next_steps(db, actor, patient_id)
    step = entry.live_row(db, actor, NextStep, patient_id, step_id)
    entry.correct(db, actor, NEXT_STEP, step, _step_fields(step), change, change.reason, required=("kind", "description"))
    [row] = _step_rows(db, actor, [step])
    return row


def remove_next_step(db: Session, actor: Actor, patient_id: uuid.UUID, step_id: uuid.UUID, reason: str) -> None:
    _require_next_steps(db, actor, patient_id)
    step = entry.live_row(db, actor, NextStep, patient_id, step_id)
    audit.soft_delete(db, actor, step, subject_table=NEXT_STEP, reason=reason, before=_step_fields(step))
