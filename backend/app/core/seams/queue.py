"""Job queue interface (ADR 0003): durable background work. The database queue now; a managed queue later.

Jobs run as named steps. A retry resumes after the last completed step, so each step must be safe to run
again if a worker dies between doing it and recording it (at-least-once). Payloads, step outputs and errors
hold **IDs only** (design doc §6.4): UUIDs, counts, flags, dates and short codes, never names, identifiers,
text or file contents. The queue refuses anything else. Contract tests: tests/seams/test_queue.py.
"""

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol

# A short code: lowercase letters, digits and . _ : - (e.g. "refresh_pbs", "source_unreachable", "2026-09-01").
CODE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,63}$")
DEFAULT_LEASE = timedelta(minutes=15)


class UnknownJobKind(ValueError):
    """No such Job Kind in the registry: the Job is refused (design doc §6.3)."""


class UnknownJob(LookupError):
    """No Job with that id."""


class ModuleInactive(ValueError):
    """The Job Kind belongs to a Specialty Module that isn't active for the Job's Practice."""


class NotIdsOnly(ValueError):
    """A payload, step output or error held something other than IDs, counts, flags, dates or short codes."""


@dataclass(frozen=True)
class NewJob:
    kind: str
    practice_id: uuid.UUID | None = None  # None: system-wide, e.g. a Refresh
    payload: Mapping[str, Any] = field(default_factory=dict)
    priority: int = 0
    max_attempts: int = 3
    run_after_seconds: int = 0


@dataclass(frozen=True)
class ClaimedJob:
    id: uuid.UUID
    kind: str
    practice_id: uuid.UUID | None
    payload: dict[str, Any]
    attempt: int
    # Steps finished by earlier attempts, with their outputs: a retry resumes after them.
    completed_steps: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class StepStatus:
    name: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None


@dataclass(frozen=True)
class JobStatus:
    id: uuid.UUID
    kind: str
    practice_id: uuid.UUID | None
    status: str  # queued / running / succeeded / failed / cancelled
    attempts: int
    max_attempts: int
    created_at: datetime
    finished_at: datetime | None
    last_error: str | None
    steps: list[StepStatus]


class JobQueue(Protocol):
    def enqueue(self, job: NewJob) -> uuid.UUID:
        """Refuses an unknown Job Kind, a module's Job Kind for a Practice without that module active, and
        anything but IDs in the payload."""
        ...

    def claim(self, worker_id: str, kinds: Sequence[str], lease: timedelta = DEFAULT_LEASE) -> ClaimedJob | None:
        """The next due Job of one of `kinds`, locked for this worker, or None. A Job still running after
        `lease` belonged to a worker that died, and is claimed again. A Job whose module was switched off for
        its Practice is cancelled, not run."""
        ...

    def step_done(self, job_id: uuid.UUID, name: str, output: Mapping[str, Any]) -> None: ...

    def succeed(self, job_id: uuid.UUID) -> None: ...

    def fail(self, job_id: uuid.UUID, error: str, retry_after_seconds: int = 30) -> None:
        """`error` is a short code. Retried until `max_attempts`, then failed for good."""
        ...

    def status(self, job_id: uuid.UUID) -> JobStatus:
        """Raises UnknownJob for an id it doesn't know."""
        ...

    def latest(self, kind: str) -> JobStatus | None:
        """The most recently enqueued Job of a kind, e.g. to show the last Refresh."""
        ...


def ids_only(values: Mapping[str, Any]) -> None:
    """Raises NotIdsOnly unless every key and value is an ID, count, flag, date or short code."""
    for key, value in values.items():
        if not CODE.match(key):
            raise NotIdsOnly(f"key {key!r} isn't a short code")
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not _is_id_like(item):
                raise NotIdsOnly(f"{key}: only IDs, counts, flags, dates and short codes are allowed")


def check_code(error: str) -> None:
    if not CODE.match(error):
        raise NotIdsOnly("an error is a short code, never free text")


def _is_id_like(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int, float)):
        return True
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return bool(CODE.match(value))
