"""The durable job queue (design doc §3, §6.3). Payloads and errors hold IDs only, never Patient data."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SharedEntity, SupportEntity, allowed
from app.core.vocabulary import RUN_STATUSES

JOB_STEP_STATUSES = ("pending", "running", "succeeded", "failed", "skipped")


class JobKind(SharedEntity):
    """Every Job Kind. A Job of an unknown kind is rejected by the database (FK)."""

    __tablename__ = "job_kind"
    __extra_args__ = (UniqueConstraint("key"),)

    key: Mapped[str]
    module_key: Mapped[str | None] = mapped_column(
        ForeignKey("specialty_module.key", ondelete="RESTRICT"), index=True
    )
    description: Mapped[str]


class Job(SupportEntity):
    """`practice_id` is null for system-wide Jobs such as a Refresh."""

    __tablename__ = "job"
    __extra_args__ = (
        CheckConstraint("attempts >= 0 AND attempts <= max_attempts", name="attempts"),
        CheckConstraint("max_attempts >= 1", name="max_attempts"),
        Index("ix_job_claim", "status", "run_after", "priority"),
    )

    kind: Mapped[str] = mapped_column(ForeignKey("job_kind.key", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(info=allowed(*RUN_STATUSES), server_default=text("'queued'"))
    payload: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    priority: Mapped[int] = mapped_column(server_default=text("0"))
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(server_default=text("3"))
    run_after: Mapped[datetime] = mapped_column(server_default=text("now()"))
    locked_at: Mapped[datetime | None]
    locked_by: Mapped[str | None]
    last_error: Mapped[str | None]
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_run.id", ondelete="RESTRICT"), index=True
    )
    finished_at: Mapped[datetime | None]


class JobStep(SharedEntity):
    """One resumable step of a Job. Reached through its Job, so it carries no `practice_id`."""

    __tablename__ = "job_step"
    __extra_args__ = (
        UniqueConstraint("job_id", "sequence"),
        CheckConstraint("sequence >= 0", name="sequence"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int]
    name: Mapped[str]
    status: Mapped[str] = mapped_column(
        info=allowed(*JOB_STEP_STATUSES), server_default=text("'pending'")
    )
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    output: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    error_detail: Mapped[str | None]
