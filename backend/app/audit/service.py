"""The audit spine's service interface: record a Verification, read a subject's history (design doc §6.3)."""

import uuid
from typing import Any, Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import Verification
from app.audit.schemas import VerificationEntry
from app.core.vocabulary import JobTitle

VerificationAction = Literal[
    "accept",
    "edit",
    "reject",
    "override",
    "attribute",
    "sign_off_export",
    "delete",
    "move",
    "hold",
    "activate_module",
    "deactivate_module",
]


class Actor(Protocol):
    """The signed-in User acting. The accounts module's CurrentUser fits."""

    @property
    def id(self) -> uuid.UUID: ...
    @property
    def practice_id(self) -> uuid.UUID: ...
    @property
    def job_title(self) -> JobTitle: ...


def record_verification(
    db: Session,
    actor: Actor,
    *,
    subject_table: str,
    subject_id: uuid.UUID,
    action: VerificationAction,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    reauthenticated: bool = False,
) -> uuid.UUID:
    """`reauthenticated` stays False until Stage 13 adds re-authentication (revisit-later #21)."""
    verification = Verification(
        practice_id=actor.practice_id,
        subject_table=subject_table,
        subject_id=subject_id,
        user_id=actor.id,
        job_title_at_time=actor.job_title,
        action=action,
        before=before,
        after=after,
        reason=reason,
        reauthenticated=reauthenticated,
    )
    db.add(verification)
    db.flush()
    return verification.id


def history(db: Session, practice_id: uuid.UUID, subject_table: str, subject_id: uuid.UUID) -> list[VerificationEntry]:
    """Newest first."""
    rows = db.scalars(
        select(Verification)
        .where(
            Verification.practice_id == practice_id,
            Verification.subject_table == subject_table,
            Verification.subject_id == subject_id,
        )
        .order_by(Verification.created_at.desc(), Verification.id)
    )
    return [
        VerificationEntry(
            action=v.action,
            user_id=v.user_id,
            job_title_at_time=v.job_title_at_time,
            before=v.before,
            after=v.after,
            reason=v.reason,
            reauthenticated=v.reauthenticated,
            at=v.created_at,
        )
        for v in rows
    ]
