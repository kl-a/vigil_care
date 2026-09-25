"""Accounts service: who may sign in, and who is signed in. Returns schemas, never models (§14).

A User is the person (one login); their Job Title and active status belong to a Practice Membership, one per
Practice. A session acts in one Practice at a time, so everything here is about the current Practice.
"""

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.core.permissions import require
from app.core.seams.identity import DevLogin, DevLoginCredentials, LoginRefused
from app.core.vocabulary import JOB_TITLES
from app.modules.accounts.models import PracticeMembership, User
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


def _memberships() -> Select[User, PracticeMembership]:
    """Each User with one of their Memberships; the soft-delete filter drops deleted Users and Memberships."""
    return select(User, PracticeMembership).join(PracticeMembership, PracticeMembership.user_id == User.id)


def signed_in_user(db: Session, user_id: uuid.UUID, practice_id: uuid.UUID) -> CurrentUser | None:
    """The User behind a session, acting in `practice_id`, if their Membership there is still active."""
    row = db.execute(
        _memberships().where(User.id == user_id, PracticeMembership.practice_id == practice_id, PracticeMembership.is_active)
    ).one_or_none()
    if row is None:
        return None
    user, membership = row
    names = practice_names(db, {practice_id})
    if practice_id not in names:
        return None
    return CurrentUser(
        id=user.id,
        display_name=user.display_name,
        job_title=membership.job_title,
        practice_id=practice_id,
        practice_name=names[practice_id],
    )


def dev_login_choices(db: Session) -> list[DevLoginChoice]:
    """Every active Membership is its own choice: a User at two Practices appears twice."""
    rows = db.execute(_memberships().where(PracticeMembership.is_active)).all()
    names = practice_names(db, {membership.practice_id for _, membership in rows})
    choices = [
        DevLoginChoice(
            id=user.id,
            display_name=user.display_name,
            job_title=membership.job_title,
            practice_id=membership.practice_id,
            practice_name=names[membership.practice_id],
        )
        for user, membership in rows
        if membership.practice_id in names
    ]
    return sorted(choices, key=lambda c: (c.practice_name, JOB_TITLES.index(c.job_title), c.display_name))


def dev_login(db: Session, user_id: uuid.UUID, practice_id: uuid.UUID) -> CurrentUser:
    """Dev only (the route exists only in dev). Raises LoginRefused unless the Membership is active."""
    DevLogin(ActiveUsers(db)).authenticate(DevLoginCredentials(user_id))
    user = signed_in_user(db, user_id, practice_id)
    if user is None:
        raise LoginRefused()
    _membership(db, practice_id, user_id).last_login_at = func.now()
    return user


class ActiveUsers:
    """The accounts module's answer to the identity interface's `ActiveUsers`: active at any Practice."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def is_active(self, user_id: uuid.UUID) -> bool:
        active = _memberships().where(User.id == user_id, PracticeMembership.is_active).limit(1)
        return self._db.execute(active).first() is not None


# --- User Management (#6). Only Job Titles with "manage_users" (design doc §6.4). ---------------

# Verifications about a User's Membership use this subject_table, scoped to the Practice like any Verification.
USER_SUBJECT = "user"

# Not a password hash: a new User can't sign in with a password until they enrol (Stage 13).
NO_PASSWORD = "!no-password-until-enrolment"


class UserNotFound(LookupError):
    """No such User in the actor's Practice (Users with no Membership here are invisible)."""


class UsernameTaken(ValueError):
    pass


class DisplayNameNeeded(ValueError):
    """A brand new login needs a display name; someone with a login elsewhere brings their own."""


class CantChangeYourself(ValueError):
    """Your own Job Title and active status are changed by someone else, so nobody locks themselves out."""


def _row(user: User, membership: PracticeMembership) -> UserRow:
    return UserRow(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        job_title=membership.job_title,
        is_active=membership.is_active,
        last_login_at=membership.last_login_at,
        provider_id=membership.provider_id,
    )


def _membership(db: Session, practice_id: uuid.UUID, user_id: uuid.UUID) -> PracticeMembership:
    membership = db.scalars(
        select(PracticeMembership).where(PracticeMembership.practice_id == practice_id, PracticeMembership.user_id == user_id)
    ).one_or_none()
    if membership is None:
        raise UserNotFound()
    return membership


def list_users(db: Session, actor: CurrentUser) -> list[UserRow]:
    """The current Practice's Memberships. Nothing about anyone's other Practices."""
    require(actor.job_title, "manage_users")
    rows = db.execute(_memberships().where(PracticeMembership.practice_id == actor.practice_id).order_by(User.display_name))
    return [_row(user, membership) for user, membership in rows]


def user_detail(db: Session, actor: CurrentUser, user_id: uuid.UUID) -> UserDetail:
    require(actor.job_title, "manage_users")
    membership = _membership(db, actor.practice_id, user_id)
    user = db.get_one(User, user_id)
    # Verifications belong to a Practice, so this is the history at this Practice only.
    entries = audit.history(db, actor.practice_id, USER_SUBJECT, user_id)
    authors = db.execute(select(User.id, User.display_name).where(User.id.in_({e.user_id for e in entries})))
    names = {author_id: name for author_id, name in authors}
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
    return UserDetail(**_row(user, membership).model_dump(), history=history)


def create_user(db: Session, actor: CurrentUser, new: NewUser) -> UserRow:
    """Adds someone to the current Practice. If they already have a login (at another Practice), they're found
    by username and keep their own display name; otherwise a new login is made."""
    require(actor.job_title, "manage_users")
    user = db.scalars(select(User).where(User.username == new.username).execution_options(include_deleted=True)).one_or_none()
    if user is not None and user.deleted_at is not None:
        raise UsernameTaken(f"The username {new.username} belonged to a removed login and can't be reused.")
    if user is None:
        if new.display_name is None:
            raise DisplayNameNeeded("A new login needs a display name.")
        user = User(username=new.username, display_name=new.display_name, password_hash=NO_PASSWORD)
        db.add(user)
        db.flush()
    joined = select(PracticeMembership.id).where(
        PracticeMembership.practice_id == actor.practice_id, PracticeMembership.user_id == user.id
    )
    if db.scalars(joined.execution_options(include_deleted=True)).first() is not None:
        raise UsernameTaken(f"{new.username} is already a User of this Practice.")
    membership = PracticeMembership(practice_id=actor.practice_id, user_id=user.id, job_title=new.job_title)
    db.add(membership)
    db.flush()
    # Joining a Practice grants a Job Title there, so it's recorded like any Job Title change.
    _record_change(db, actor, user, before=None, after={"job_title": new.job_title, "username": new.username})
    db.refresh(membership)
    return _row(user, membership)


def change_user(db: Session, actor: CurrentUser, user_id: uuid.UUID, change: UserChange) -> UserRow:
    """Changes the User's Membership at the current Practice only; their other Practices are untouched."""
    require(actor.job_title, "manage_users")
    membership = _membership(db, actor.practice_id, user_id)
    user = db.get_one(User, user_id)
    if user.id == actor.id and (change.job_title is not None or change.is_active is not None):
        raise CantChangeYourself("You can't change your own Job Title or deactivate yourself; ask another User.")
    reason = (change.reason or "").strip() or None
    if change.job_title is not None and change.job_title != membership.job_title:
        _record_change(db, actor, user, {"job_title": membership.job_title}, {"job_title": change.job_title}, reason)
        membership.job_title = change.job_title
    if change.is_active is not None and change.is_active != membership.is_active:
        _record_change(db, actor, user, {"is_active": membership.is_active}, {"is_active": change.is_active}, reason)
        membership.is_active = change.is_active
    db.flush()
    return _row(user, membership)


def _record_change(
    db: Session,
    actor: CurrentUser,
    user: User,
    before: dict[str, object] | None,
    after: dict[str, object],
    reason: str | None = None,
) -> None:
    """Every change to a User is an `edit` Verification; before/after say what changed (design doc §6.3)."""
    audit.record_verification(
        db, actor, subject_table=USER_SUBJECT, subject_id=user.id, action="edit", before=before, after=after, reason=reason
    )
