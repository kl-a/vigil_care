import uuid

from pydantic import BaseModel

from app.core.vocabulary import JobTitle


class CurrentUser(BaseModel):
    """The signed-in User, as the frontend sees them."""

    id: uuid.UUID
    display_name: str
    job_title: JobTitle
    practice_id: uuid.UUID
    practice_name: str


class DevLoginChoice(BaseModel):
    """A User who can be chosen at the dev login."""

    id: uuid.UUID
    display_name: str
    job_title: JobTitle
    practice_name: str


class DevLoginRequest(BaseModel):
    user_id: uuid.UUID
