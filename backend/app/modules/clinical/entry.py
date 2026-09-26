"""Entering the Clinical Record by hand (#35, design doc §6.2–6.4): the pattern every Clinical Record kind follows.

- **Who:** Verification Rights for the Practice's active modules decide who may enter each fact kind; the
  service refuses anyone else (403). Everyone who may view Patient data may read it; developer admins never.
- **Provenance:** a row entered by hand carries `entered_by_user_id`; `source_fact_id` stays null.
- **Verifications:** adding is an `edit` Verification with only `after`; a correction is an `edit` with before,
  after and a **reason, given once per save**; removal is a soft delete with a reason (`audit.soft_delete`).
"""

import uuid
from collections.abc import Collection, Iterable
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.models import Verification
from app.audit.service import Actor
from app.core.base_model import Entity
from app.core.changes import blank_to_none, changed_fields
from app.core.permissions import NotAllowed, VerificationRights, require
from app.modules.accounts.service import display_names
from app.modules.clinical.schemas import Entered, ModuleFacts
from app.modules.patients.service import patient_names
from app.modules.registry.registry import installed_modules
from app.modules.registry.service import active_module_keys, configuration


class PatientNotFound(LookupError):
    """No such live Patient in the actor's Practice."""


class RecordNotFound(LookupError):
    """No such live Clinical Record row for this Patient."""


def rights(db: Session, actor: Actor) -> VerificationRights:
    """Verification Rights of the Practice's active modules, plus the Core's."""
    return configuration(db, actor.practice_id).verification_rights


def entry_rights(db: Session, actor: Actor) -> dict[str, bool]:
    """Which fact kinds the actor may enter by hand, for the UI's locks."""
    require(actor.job_title, "view_patient_data")
    active = rights(db, actor)
    return {kind: active.can_verify(actor.job_title, kind) for kind in sorted(active.fact_kinds())}


def require_view(db: Session, actor: Actor, patient_id: uuid.UUID) -> None:
    require(actor.job_title, "view_patient_data")
    if not patient_names(db, actor.practice_id, {patient_id}):
        raise PatientNotFound()


def require_entry(db: Session, actor: Actor, patient_id: uuid.UUID, fact_kind: str) -> None:
    """The actor may enter `fact_kind` for this Patient, or NotAllowed (403) / PatientNotFound (404)."""
    require_view(db, actor, patient_id)
    active = rights(db, actor)
    if fact_kind not in active.fact_kinds() or not active.can_verify(actor.job_title, fact_kind):
        raise NotAllowed("Your Job Title can't enter this.")


def entered_by(actor: Actor) -> dict[str, Any]:
    """Provenance of a row entered by hand, scoped to the actor's Practice."""
    return {"practice_id": actor.practice_id, "entered_by_user_id": actor.id}


def record_added(db: Session, actor: Actor, subject_table: str, row: Entity, fields: dict[str, Any]) -> None:
    db.flush()
    audit.record_verification(db, actor, subject_table=subject_table, subject_id=row.id, action="edit", after=fields)


def correct(
    db: Session,
    actor: Actor,
    subject_table: str,
    row: Entity,
    current: dict[str, Any],
    change: BaseModel,
    reason: str,
    required: Collection[str] = (),
) -> None:
    """Applies the fields of `change` that differ from `current` (the row as its Verifications record it) and
    records one Verification for the whole save, with the reason. Nothing changed, nothing recorded."""
    changed = changed_fields(current, change, required=required, mode="json", exclude=("reason",))
    if not changed:
        return
    for field, value in blank_to_none(change.model_dump(exclude_unset=True, exclude={"reason"})).items():
        if field in changed:
            setattr(row, field, value)
    audit.record_verification(
        db, actor, subject_table=subject_table, subject_id=row.id, action="edit",
        before={field: current[field] for field in changed}, after=changed, reason=reason,
    )
    db.flush()


def entered(db: Session, practice_id: uuid.UUID, subject_table: str, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Entered]:
    """Who entered each row, with their Job Title then, and when: its first Verification."""
    wanted = set(ids)
    if not wanted:
        return {}
    rows = db.execute(
        select(Verification.subject_id, Verification.user_id, Verification.job_title_at_time, Verification.created_at)
        .where(Verification.practice_id == practice_id, Verification.subject_table == subject_table, Verification.subject_id.in_(wanted))
        .order_by(Verification.created_at, Verification.id)
    ).all()
    first: dict[uuid.UUID, Any] = {}
    for row in rows:
        first.setdefault(row.subject_id, row)
    names = display_names(db, {row.user_id for row in first.values()})
    return {
        subject: Entered(by=names.get(row.user_id, "Unknown User"), job_title=row.job_title_at_time, at=row.created_at)
        for subject, row in first.items()
    }


def inactive_module_facts(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[ModuleFacts]:
    """Installed Specialty Modules not active at this Practice, with the Patient's facts each recorded, in plain
    words (ADR 0004, amended). Modules with nothing recorded are left out."""
    require_view(db, actor, patient_id)
    active = set(active_module_keys(db, actor.practice_id))
    found = []
    for key, module in installed_modules().items():
        if key in active or module.read_only_view is None:
            continue
        facts = module.read_only_view(db, actor.practice_id, patient_id)
        if facts:
            found.append(ModuleFacts(module=key, display_name=module.display_name, facts=facts))
    return found
