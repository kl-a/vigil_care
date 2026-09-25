"""Extractions, Extracted Facts (the unit of review) and the fact-kind registry (design doc §6.3)."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, SharedEntity, allowed, practice_fk
from app.core.vocabulary import CONFIDENCE_LEVELS, VERIFYING_JOB_TITLES

EXTRACTION_READERS = ("text_layer", "classic_ocr", "local_vlm", "cloud_vlm")
REVIEW_STATUSES = ("pending", "accepted", "edited", "rejected", "withdrawn")
NUMERIC_CROSSCHECKS = ("agree", "disagree", "not_applicable")


class FactKind(SharedEntity):
    """Every kind of Extracted Fact. The Core and each Specialty Module add rows in their migrations."""

    __tablename__ = "fact_kind"
    __extra_args__ = (UniqueConstraint("key"),)

    key: Mapped[str]
    module_key: Mapped[str | None] = mapped_column(
        ForeignKey("specialty_module.key", ondelete="RESTRICT"), index=True
    )
    # The Clinical Record table an accepted fact of this kind lands in.
    record_table: Mapped[str]


class Extraction(PracticeEntity):
    __tablename__ = "extraction"
    __extra_args__ = (practice_fk("document_id", "document", ondelete="CASCADE"),)

    document_id: Mapped[uuid.UUID] = mapped_column(index=True)
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_type.id", ondelete="RESTRICT"), index=True
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_run.id", ondelete="RESTRICT"), index=True
    )
    reader: Mapped[str] = mapped_column(info=allowed(*EXTRACTION_READERS))
    model_id: Mapped[str | None]
    prompt_version: Mapped[str | None]


class ExtractedFact(PracticeEntity):
    __tablename__ = "extracted_fact"
    __extra_args__ = (
        practice_fk("extraction_id", "extraction"),
        practice_fk("patient_id", "patient"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        Index("ix_extracted_fact_review_queue", "review_status", "required_job_title"),
    )

    extraction_id: Mapped[uuid.UUID] = mapped_column(index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    fact_kind: Mapped[str] = mapped_column(
        ForeignKey("fact_kind.key", ondelete="RESTRICT"), index=True
    )
    module_key: Mapped[str | None] = mapped_column(
        ForeignKey("specialty_module.key", ondelete="RESTRICT"), index=True
    )
    payload: Mapped[dict[str, Any]]
    source_locations: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    confidence: Mapped[Decimal]
    confidence_band: Mapped[str] = mapped_column(info=allowed(*CONFIDENCE_LEVELS))
    numeric_crosscheck: Mapped[str] = mapped_column(
        info=allowed(*NUMERIC_CROSSCHECKS), server_default=text("'not_applicable'")
    )
    # Never developer_admin: they can't verify anything (design doc §6.4).
    required_job_title: Mapped[str] = mapped_column(info=allowed(*VERIFYING_JOB_TITLES))
    review_status: Mapped[str] = mapped_column(
        info=allowed(*REVIEW_STATUSES), server_default=text("'pending'")
    )
    accepted_record_table: Mapped[str | None]
    accepted_record_id: Mapped[uuid.UUID | None]
