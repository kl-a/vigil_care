"""Audit spine and support data: Verification, pipeline runs, model call log and cache (design doc §6.3)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, SharedEntity, SupportEntity, allowed, practice_fk
from app.core.vocabulary import JOB_TITLES, RUN_STATUSES

VERIFICATION_ACTIONS = (
    "accept",
    "edit",
    "reject",
    "override",
    "attribute",
    "sign_off_export",
    "delete",
    "move",
    "hold",
    "activate_module",
    "deactivate_module",
)
PIPELINE_RUN_KINDS = (
    "ingest",
    "extract",
    "match",
    "report",
    "pbs_refresh",
    "trial_refresh",
    "eviq_refresh",
    "ocr",
    "mask",
    "redaction_job",
    "reference_set_eval",
)
LLM_ENDPOINTS = ("local_vlm", "cloud")


class Verification(PracticeEntity):
    """A User's sign-off on anything. Never changes once written."""

    __tablename__ = "verification"
    __immutable__ = True
    __extra_args__ = (
        practice_fk("user_id", "user"),
        Index("ix_verification_subject", "subject_table", "subject_id"),
    )

    subject_table: Mapped[str]
    subject_id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    job_title_at_time: Mapped[str] = mapped_column(info=allowed(*JOB_TITLES))
    action: Mapped[str] = mapped_column(info=allowed(*VERIFICATION_ACTIONS))
    reason: Mapped[str | None]
    before: Mapped[dict[str, Any] | None]
    after: Mapped[dict[str, Any] | None]
    reauthenticated: Mapped[bool] = mapped_column(server_default=text("false"))


class PipelineRun(SupportEntity):
    """IDs only in `inputs` and `error_detail`: never Patient data."""

    __tablename__ = "pipeline_run"

    kind: Mapped[str] = mapped_column(info=allowed(*PIPELINE_RUN_KINDS))
    status: Mapped[str] = mapped_column(info=allowed(*RUN_STATUSES), server_default=text("'queued'"))
    inputs: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    versions: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    error_detail: Mapped[str | None]


class LlmCallLog(SupportEntity):
    """Every model call, local or cloud. Never changes once written."""

    __tablename__ = "llm_call_log"
    __immutable__ = True

    pipeline_step: Mapped[str]
    endpoint: Mapped[str] = mapped_column(info=allowed(*LLM_ENDPOINTS))
    cloud_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cloud_request.id", ondelete="RESTRICT"), index=True
    )
    model_id: Mapped[str]
    prompt_version: Mapped[str | None]
    tokens_in: Mapped[int | None]
    tokens_out: Mapped[int | None]
    cost_aud: Mapped[Decimal | None]
    latency_ms: Mapped[int | None]
    input_hash: Mapped[str]
    cache_hit: Mapped[bool] = mapped_column(server_default=text("false"))


class LlmCache(SharedEntity):
    """Content-addressed model response cache. The app may hard-delete here (it's a cache)."""

    __tablename__ = "llm_cache"
    __extra_args__ = (UniqueConstraint("cache_key"),)

    cache_key: Mapped[str]
    response: Mapped[dict[str, Any]]
