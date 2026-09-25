"""Accounts service: who may sign in, and who is signed in. Returns schemas, never models (§14)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.vocabulary import JOB_TITLES
from app.modules.accounts.models import User
from app.modules.accounts.schemas import CurrentUser, DevLoginChoice
from app.modules.practice.service import practice_names


def signed_in_user(db: Session, user_id: uuid.UUID) -> CurrentUser | None:
    """The User behind a session, if they may still use Vigil (active, not soft-deleted)."""
    user = db.scalars(select(User).where(User.id == user_id, User.is_active)).one_or_none()
    if user is None:
        return None
    names = practice_names(db, {user.practice_id})
    if user.practice_id not in names:
        return None
    return CurrentUser(
        id=user.id,
        display_name=user.display_name,
        job_title=user.job_title,  # type: ignore[arg-type]  # the database CHECK guarantees a JobTitle
        practice_id=user.practice_id,
        practice_name=names[user.practice_id],
    )


def dev_login_choices(db: Session) -> list[DevLoginChoice]:
    users = db.scalars(select(User).where(User.is_active)).all()
    names = practice_names(db, {u.practice_id for u in users})
    choices = [
        DevLoginChoice(
            id=u.id,
            display_name=u.display_name,
            job_title=u.job_title,  # type: ignore[arg-type]
            practice_name=names[u.practice_id],
        )
        for u in users
        if u.practice_id in names
    ]
    return sorted(choices, key=lambda c: (c.practice_name, JOB_TITLES.index(c.job_title), c.display_name))


class ActiveUsers:
    """The accounts module's answer to the identity interface's `ActiveUsers`."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def is_active(self, user_id: uuid.UUID) -> bool:
        return signed_in_user(self._db, user_id) is not None
