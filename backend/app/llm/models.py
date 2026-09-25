"""The cloud request ledger: every payload sent outside the Practice Boundary (design doc §4, §6.3)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SupportEntity, allowed, practice_fk

CLOUD_PURPOSES = ("vlm_read", "classify", "extract", "adjudicate", "parse_criteria")
PAYLOAD_KINDS = ("masked_image", "pseudonymised_text", "public_text")
CLOUD_REQUEST_STATUSES = ("pending", "sent", "received", "failed")


class CloudRequest(SupportEntity):
    """Written as `pending` before anything is sent; only `request_id` leaves the Practice Boundary.

    Support data (IDs only). `practice_id` is null only for public text, e.g. parsing a trial's criteria.
    After insert, only `status`, `sent_at` and `response_received_at` may change (migration trigger).
    """

    __tablename__ = "cloud_request"
    __extra_args__ = (
        UniqueConstraint("request_id"),
        # Composite FKs keep a Document or User in the request's Practice. They're skipped when
        # practice_id is null, so the plain FKs below still check the rows exist.
        practice_fk("document_id", "document"),
        practice_fk("initiated_by_user_id", "user"),
        ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["initiated_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        CheckConstraint(
            "(payload_kind = 'public_text' AND document_id IS NULL)"
            " OR (payload_kind <> 'public_text' AND practice_id IS NOT NULL AND document_id IS NOT NULL)",
            name="patient_payload_has_document",
        ),
    )

    request_id: Mapped[uuid.UUID] = mapped_column(server_default=text("gen_random_uuid()"))
    document_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    page_numbers: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    purpose: Mapped[str] = mapped_column(info=allowed(*CLOUD_PURPOSES))
    payload_kind: Mapped[str] = mapped_column(info=allowed(*PAYLOAD_KINDS))
    payload_sha256: Mapped[str]
    # Required in on-click mode; nullable for the automatic mode later.
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    model_id: Mapped[str]
    sent_at: Mapped[datetime | None]
    response_received_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(
        info=allowed(*CLOUD_REQUEST_STATUSES), server_default=text("'pending'")
    )
