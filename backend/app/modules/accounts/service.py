"""Accounts service: who may sign in, and who is signed in. Returns schemas, never models (§14)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import service as audit

from app.core.seams.identity import DevLogin, DevLoginCredentials, LoginRefused
from app.core.vocabulary import JOB_TITLES
from app.modules.accounts.models import User
from app.modules.accounts.schemas import (
    CurrentUser,
    DevLoginChoice,
    HistoryEntry,
    NewUser,
    UserChange,
    UserDetail,
    UserRow,
)
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
        job_title=user.job_title,
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
            job_title=u.job_title,
            practice_name=names[u.practice_id],
        )
        for u in users
        if u.practice_id in names
    ]
    return sorted(choices, key=lambda c: (c.practice_name, JOB_TITLES.index(c.job_title), c.display_name))


def dev_login(db: Session, user_id: uuid.UUID) -> CurrentUser:
    """Dev only (the route exists only in dev). Raises LoginRefused unless the User is active."""
    DevLogin(ActiveUsers(db)).authenticate(DevLoginCredentials(user_id))
    user = signed_in_user(db, user_id)
    if user is None:
        raise LoginRefused()
    db.get_one(User, user_id).last_login_at = func.now()
    return user


class ActiveUsers:
    """The accounts module's answer to the identity interface's `ActiveUsers`."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def is_active(self, user_id: uuid.UUID) -> bool:
        return signed_in_user(self._db, user_id) is not None


# --- User Management (#6). Callers check the "manage_users" permission first. ---------------

# Not a password hash: a new User can't sign in with a password until they enrol (Stage 13).
NO_PASSWORD = "!no-password-until-enrolment"


class UserNotFound(LookupError):
    """No such User in the actor's Practice (other Practices' Users are invisible)."""


class UsernameTaken(ValueError):
    pass


class CantChangeYourself(ValueError):
    """Your own Job Title and active status are changed by someone else, so nobody locks themselves out."""


def _row(user: User) -> UserRow:
    return UserRow(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        job_title=user.job_title,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        provider_id=user.provider_id,
    )


def _in_practice(db: Session, practice_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = db.scalars(select(User).where(User.id == user_id, User.practice_id == practice_id)).one_or_none()
    if user is None:
        raise UserNotFound()
    return user


def list_users(db: Session, practice_id: uuid.UUID) -> list[UserRow]:
    users = db.scalars(select(User).where(User.practice_id == practice_id).order_by(User.display_name))
    return [_row(u) for u in users]


def user_detail(db: Session, practice_id: uuid.UUID, user_id: uuid.UUID) -> UserDetail:
    user = _in_practice(db, practice_id, user_id)
    entries = audit.history(db, practice_id, "user", user_id)
    authors = db.execute(select(User.id, User.display_name).where(User.id.in_({e.user_id for e in entries})))
    names = {user_id: name for user_id, name in authors}
    history = [
        HistoryEntry(
            action=e.action,
            by_display_name=names.get(e.user_id, "Unknown User"),
            by_job_title=e.job_title_at_time,
            before=e.before,
            after=e.after,
            reason=e.reason,
            reauthenticated=e.reauthenticated,
            at=e.at,
        )
        for e in entries
    ]
    return UserDetail(**_row(user).model_dump(), history=history)


def create_user(db: Session, actor: CurrentUser, new: NewUser) -> UserRow:
    taken = select(User.id).where(User.practice_id == actor.practice_id, User.username == new.username)
    if db.scalars(taken.execution_options(include_deleted=True)).first() is not None:
        raise UsernameTaken(f"The username {new.username} is already in use in this Practice.")
    user = User(
        practice_id=actor.practice_id,
        username=new.username,
        display_name=new.display_name,
        password_hash=NO_PASSWORD,
        job_title=new.job_title,
    )
    db.add(user)
    db.flush()
    # Creating a User grants their first Job Title, so it's recorded like any Job Title change.
    audit.record_verification(
        db, actor, subject_table="user", subject_id=user.id, action="edit",
        after={"job_title": new.job_title, "username": new.username},
    )
    db.refresh(user)
    return _row(user)


def change_user(db: Session, actor: CurrentUser, user_id: uuid.UUID, change: UserChange) -> UserRow:
    user = _in_practice(db, actor.practice_id, user_id)
    if user.id == actor.id and (change.job_title is not None or change.is_active is not None):
        raise CantChangeYourself("You can't change your own Job Title or deactivate yourself; ask another User.")
    reason = (change.reason or "").strip() or None
    if change.job_title is not None and change.job_title != user.job_title:
        audit.record_verification(
            db, actor, subject_table="user", subject_id=user.id, action="edit",
            before={"job_title": user.job_title}, after={"job_title": change.job_title}, reason=reason,
        )
        user.job_title = change.job_title
    if change.is_active is not None and change.is_active != user.is_active:
        audit.record_verification(
            db, actor, subject_table="user", subject_id=user.id, action="edit",
            before={"is_active": user.is_active}, after={"is_active": change.is_active}, reason=reason,
        )
        user.is_active = change.is_active
    db.flush()
    return _row(user)
