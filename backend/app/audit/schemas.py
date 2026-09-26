import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, StringConstraints

from app.core.vocabulary import JobTitle


class VerificationEntry(BaseModel):
    """One sign-off, as recorded: who (id and Job Title at the time), what, and when."""

    action: str
    user_id: uuid.UUID
    job_title_at_time: JobTitle
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    reauthenticated: bool
    at: datetime


class Removal(BaseModel):
    """Soft-deleting anything needs a reason (design doc §6.2)."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class PipelineRunView(BaseModel):
    """A pipeline run, as Support Views show it: IDs, kinds, states and timings only (§6.4)."""

    id: uuid.UUID
    kind: str
    status: str
    system_wide: bool
    inputs: dict[str, Any]
    versions: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_detail: str | None
