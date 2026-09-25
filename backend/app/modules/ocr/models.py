"""Classic-OCR output per page of a Working Copy (design doc §6.3)."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, allowed, practice_fk

OCR_ENGINES = ("ppocr_v5", "doctr")


class OcrPage(PracticeEntity):
    """Belongs to exactly one of a Document or a Redaction Job file."""

    __tablename__ = "ocr_page"
    __extra_args__ = (
        practice_fk("document_id", "document"),
        practice_fk("redaction_job_file_id", "redaction_job_file"),
        CheckConstraint("num_nonnulls(document_id, redaction_job_file_id) = 1", name="one_parent"),
        CheckConstraint("page_number >= 1", name="page_number_positive"),
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    redaction_job_file_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    page_number: Mapped[int]
    engine: Mapped[str] = mapped_column(info=allowed(*OCR_ENGINES))
    engine_version: Mapped[str]
    # [{text, bbox_pt, confidence}], validated by Pydantic before write.
    words: Mapped[list[Any]]
    mean_confidence: Mapped[Decimal | None]
    rotation_deg: Mapped[Decimal | None]
