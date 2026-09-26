import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobStepView(BaseModel):
    name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    output: dict[str, Any]


class JobView(BaseModel):
    """A Job's progress, as Support Views show it: IDs, kinds, states, counts and timings only (§6.4)."""

    id: uuid.UUID
    kind: str
    status: str
    system_wide: bool
    attempts: int
    max_attempts: int
    created_at: datetime
    finished_at: datetime | None
    last_error: str | None
    payload: dict[str, Any]
    steps: list[JobStepView]


class QueueDepthView(BaseModel):
    """Jobs queued and running now, and failed for good in the last day: system-wide and this Practice's."""

    queued: int
    running: int
    failed_last_day: int


class RefreshView(BaseModel):
    """A Refresh Job Kind and its most recent run."""

    kind: str
    description: str
    last_job: JobView | None


class StartRefresh(BaseModel):
    kind: str
