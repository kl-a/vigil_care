import uuid
from datetime import datetime

from pydantic import BaseModel


class JobStepView(BaseModel):
    name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None


class JobView(BaseModel):
    """A Job's progress, as Support Views show it: IDs, kinds, states, counts and timings only (§6.4)."""

    id: uuid.UUID
    kind: str
    status: str
    attempts: int
    max_attempts: int
    created_at: datetime
    finished_at: datetime | None
    last_error: str | None
    steps: list[JobStepView]


class RefreshView(BaseModel):
    """A Refresh Job Kind and its most recent run."""

    kind: str
    description: str
    last_job: JobView | None


class StartRefresh(BaseModel):
    kind: str
