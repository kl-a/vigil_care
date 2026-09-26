"""What each Job Kind does, and when scheduled ones fall due (design doc §3).

A handler is a Job Kind's named steps, run in order. A retry resumes after the last completed step, so a step
must be safe to run again. Steps return IDs-only outputs, which later steps read from `ctx.outputs`. Modules
register their handlers in `app/jobs.py`; each Job Kind is also registered by a migration (`job_kind`).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.seams.queue import ClaimedJob


@dataclass(frozen=True)
class JobContext:
    job: ClaimedJob
    sessions: sessionmaker[Session]
    settings: Settings
    # Outputs of the steps done so far, this attempt or earlier ones.
    outputs: dict[str, Mapping[str, Any]]


Step = Callable[[JobContext], Mapping[str, Any]]


class JobFailed(Exception):
    """A step failed in a way it can explain with a short code (IDs only); the Job is retried."""

    def __init__(self, code: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class JobHandler:
    kind: str
    steps: tuple[tuple[str, Step], ...]


@dataclass(frozen=True)
class Schedule:
    kind: str
    # The most recent time the Job fell due, at or before a given moment.
    due: Callable[[datetime], datetime]


def monthly(day: int) -> Callable[[datetime], datetime]:
    """Due at midnight UTC on `day` of each month (the PBS Schedule: the 1st)."""

    def last_due(now: datetime) -> datetime:
        now = now.astimezone(UTC)
        this_month = now.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
        if this_month <= now:
            return this_month
        year, month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
        return this_month.replace(year=year, month=month)

    return last_due


@dataclass
class JobRegistry:
    handlers: dict[str, JobHandler] = field(default_factory=dict)
    schedules: list[Schedule] = field(default_factory=list)

    def register(self, handler: JobHandler) -> None:
        self.handlers[handler.kind] = handler

    def schedule(self, schedule: Schedule) -> None:
        self.schedules.append(schedule)

    @property
    def kinds(self) -> list[str]:
        return sorted(self.handlers)
