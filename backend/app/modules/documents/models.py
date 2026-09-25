"""Documents and Document Types (design doc §6.3, §7.5)."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, SharedEntity, allowed, member_fk, practice_fk

DOCUMENT_STATUSES = (
    "uploaded",
    "ocr",
    "masking",
    "redaction_review",
    "classifying",
    "extracting",
    "in_review",
    "complete",
    "held",
    "failed",
)
INPUT_METHODS = ("native_pdf", "scan", "photo", "fax")
HOLD_REASONS = ("unreadable", "unknown_type", "pii_uncertain", "user_held")


class DocumentType(SharedEntity):
    """Developer-maintained registry. `module_key` is the Specialty Module that contributed it (null = Core)."""

    __tablename__ = "document_type"
    __extra_args__ = (UniqueConstraint("key"),)

    key: Mapped[str]
    display_name: Mapped[str]
    module_key: Mapped[str | None] = mapped_column(
        ForeignKey("specialty_module.key", ondelete="RESTRICT"), index=True
    )
    json_schema: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    extraction_prompt_ref: Mapped[str | None]
    version: Mapped[str]
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class Document(PracticeEntity):
    __tablename__ = "document"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        member_fk("uploaded_by_user_id"),
        member_fk("held_by_user_id"),
        UniqueConstraint("patient_id", "original_sha256"),
        CheckConstraint("(status = 'held') = (hold_reason IS NOT NULL)", name="hold_reason_when_held"),
        CheckConstraint("page_count IS NULL OR page_count >= 1", name="page_count_positive"),
        Index("ix_document_patient_id_doc_date", "patient_id", text("doc_date DESC")),
        Index("ix_document_held", "patient_id", postgresql_where=text("status = 'held'")),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    document_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_type.id", ondelete="RESTRICT"), index=True
    )
    original_uri: Mapped[str]
    original_sha256: Mapped[str]
    working_copy_uri: Mapped[str | None]
    page_count: Mapped[int | None]
    doc_date: Mapped[date | None]
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    input_method: Mapped[str] = mapped_column(info=allowed(*INPUT_METHODS))
    status: Mapped[str] = mapped_column(
        info=allowed(*DOCUMENT_STATUSES), server_default=text("'uploaded'")
    )
    hold_reason: Mapped[str | None] = mapped_column(info=allowed(*HOLD_REASONS))
    held_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
