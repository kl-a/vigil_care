import uuid

from pydantic import BaseModel

from app.core.vocabulary import JobTitle


class UserSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    job_title: JobTitle
    practice_name: str


class DevLoginChoice(UserSummary):
    """A User who can be chosen at the dev login."""


class CurrentUser(UserSummary):
    """The signed-in User, as the frontend sees them."""

    practice_id: uuid.UUID


class DevLoginRequest(BaseModel):
    user_id: uuid.UUID
