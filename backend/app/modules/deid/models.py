"""Redaction Jobs, PII detection and masking records (design doc §6.3, §9)."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, allowed, member_fk, practice_fk

REDACTION_PURPOSES = ("trial_portal", "referral", "other")
REDACTION_JOB_STATUSES = ("draft", "processing", "in_review", "complete", "failed")
PII_ENTITY_TYPES = (
    "NAME",
    "DOB",
    "MEDICARE",
    "IHI",
    "DVA",
    "MRN",
    "ADDRESS",
    "PHONE",
    "EMAIL",
    "PROVIDER_NAME",
    "REFERRING_DOCTOR",
)
ENTITY_ORIGINS = ("auto", "manual")
ENTITY_STATUSES = ("active", "removed_false_positive")


class RedactionJob(PracticeEntity):
    """Unlinked jobs (no Patient) wait in the "Unlinked" filter to be filed."""

    __tablename__ = "redaction_job"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        member_fk("created_by_user_id"),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    purpose: Mapped[str] = mapped_column(info=allowed(*REDACTION_PURPOSES))
    status: Mapped[str] = mapped_column(
        info=allowed(*REDACTION_JOB_STATUSES), server_default=text("'draft'")
    )


class RedactionJobFile(PracticeEntity):
    __tablename__ = "redaction_job_file"
    __extra_args__ = (practice_fk("redaction_job_id", "redaction_job"),)

    redaction_job_id: Mapped[uuid.UUID] = mapped_column(index=True)
    original_uri: Mapped[str]
    original_sha256: Mapped[str]
    redacted_uri: Mapped[str | None]
    redacted_sha256: Mapped[str | None]
    leak_check_passed: Mapped[bool | None]
    leak_check_report: Mapped[dict[str, Any] | None]


class RedactionLog(PracticeEntity):
    """Belongs to exactly one of a Document or a Redaction Job file."""

    __tablename__ = "redaction_log"
    __extra_args__ = (
        practice_fk("document_id", "document"),
        practice_fk("redaction_job_file_id", "redaction_job_file"),
        member_fk("reviewed_by_user_id"),
        CheckConstraint("num_nonnulls(document_id, redaction_job_file_id) = 1", name="one_parent"),
        CheckConstraint("entity_count >= 0", name="entity_count"),
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    redaction_job_file_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_run.id", ondelete="RESTRICT"), index=True
    )
    entity_count: Mapped[int] = mapped_column(server_default=text("0"))
    min_confidence: Mapped[Decimal | None]
    required_manual_review: Mapped[bool] = mapped_column(server_default=text("false"))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    leak_check_passed: Mapped[bool | None]


class RedactionEntity(PracticeEntity):
    """One PII item. Stores a hash of the text, never the plaintext."""

    __tablename__ = "redaction_entity"
    __extra_args__ = (
        practice_fk("redaction_log_id", "redaction_log"),
        CheckConstraint("page_number >= 1", name="page_number_positive"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"),
    )

    redaction_log_id: Mapped[uuid.UUID] = mapped_column(index=True)
    entity_type: Mapped[str] = mapped_column(info=allowed(*PII_ENTITY_TYPES))
    page_number: Mapped[int]
    bbox_pt: Mapped[list[Any]]
    text_hash: Mapped[str]
    replacement_token: Mapped[str | None]
    confidence: Mapped[Decimal | None]
    origin: Mapped[str] = mapped_column(info=allowed(*ENTITY_ORIGINS))
    status: Mapped[str] = mapped_column(info=allowed(*ENTITY_STATUSES), server_default=text("'active'"))
