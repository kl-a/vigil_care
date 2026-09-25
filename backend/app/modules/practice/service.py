"""Practice module service interface: what other modules may ask about Practices."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.changes import changed_fields
from app.core.permissions import require
from app.modules.practice.models import Practice
from app.modules.practice.schemas import PracticeChange, PracticeDetails


def practice_names(db: Session, practice_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    rows = db.execute(select(Practice.id, Practice.name).where(Practice.id.in_(practice_ids)))
    return {practice_id: name for practice_id, name in rows}


# --- Practice details (#14). Anyone signed in reads their own Practice; "change_settings" edits it. ---


def _as_details(practice: Practice) -> PracticeDetails:
    return PracticeDetails(
        id=practice.id,
        name=practice.name,
        address=practice.address,
        phone=practice.phone,
        fax=practice.fax,
        email=practice.email,
        abn=practice.abn,
    )


def practice_details(db: Session, actor: Actor) -> PracticeDetails:
    """Always the actor's own Practice: there is no way to name another."""
    return _as_details(db.get_one(Practice, actor.practice_id))


def change_practice(db: Session, actor: Actor, change: PracticeChange) -> PracticeDetails:
    require(actor.job_title, "change_settings")
    practice = db.get_one(Practice, actor.practice_id)
    current = _as_details(practice).model_dump()
    changed = changed_fields(current, change, required=("name",))
    if changed:
        audit.record_verification(
            db, actor, subject_table="practice", subject_id=practice.id, action="edit",
            before={field: current[field] for field in changed}, after=changed,
        )
        for field, value in changed.items():
            setattr(practice, field, value)
        db.flush()
    return _as_details(practice)
