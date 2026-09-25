import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, StringConstraints, model_validator

from app.core.vocabulary import JobTitle


class UserSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    job_title: JobTitle
    practice_name: str


class CurrentUser(UserSummary):
    """The signed-in User, acting in one Practice: `job_title` is the one they hold there."""

    practice_id: uuid.UUID


class DevLoginChoice(CurrentUser):
    """One active Practice Membership that can be chosen at the dev login."""


class DevLoginRequest(BaseModel):
    user_id: uuid.UUID
    practice_id: uuid.UUID


class UserRow(BaseModel):
    """A User as User Management lists them: their Membership at the current Practice."""

    id: uuid.UUID
    username: str
    display_name: str
    job_title: JobTitle
    is_active: bool
    last_login_at: datetime | None
    # The User's own Provider record in this Practice's directory, if linked (#7).
    provider_id: uuid.UUID | None
    provider_name: str | None


class HistoryEntry(BaseModel):
    """One Verification about a User: who changed what, when."""

    action: str
    by_display_name: str
    by_job_title: JobTitle
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    reauthenticated: bool
    at: datetime


class UserDetail(UserRow):
    history: list[HistoryEntry]


Username = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]{2,39}$")]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class NewUser(BaseModel):
    """Someone with a login at another Practice is added by username alone; a new login needs a display name."""

    username: Username
    display_name: DisplayName | None = None
    job_title: JobTitle


class UserChange(BaseModel):
    """Change a Job Title, activate or deactivate, and/or link their own Provider record (null unlinks).
    Deactivating needs a reason."""

    job_title: JobTitle | None = None
    is_active: bool | None = None
    provider_id: uuid.UUID | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _deactivation_needs_a_reason(self) -> "UserChange":
        if self.is_active is False and not (self.reason or "").strip():
            raise ValueError("Deactivating a User needs a reason.")
        return self
