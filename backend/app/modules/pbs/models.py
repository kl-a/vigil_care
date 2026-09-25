"""PBS Schedule items and Refresh history (design doc §6.3, §10.2)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SharedEntity, allowed
from app.core.vocabulary import REFRESH_STATUSES

RESTRICTION_LEVELS = (
    "unrestricted",
    "restricted",
    "authority_required",
    "authority_required_streamlined",
)


class PbsItem(SharedEntity):
    __tablename__ = "pbs_item"
    __extra_args__ = (UniqueConstraint("item_code", "schedule_date"),)

    item_code: Mapped[str]
    drug_name: Mapped[str]
    brand_names: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    restriction_level: Mapped[str] = mapped_column(info=allowed(*RESTRICTION_LEVELS))
    # Per-indication restriction levels; PBS Listing per Condition is derived from these.
    indications: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    max_quantity: Mapped[int | None]
    repeats: Mapped[int | None]
    patient_copay_general: Mapped[Decimal | None]
    patient_copay_concessional: Mapped[Decimal | None]
    schedule_date: Mapped[date]
    raw_data: Mapped[dict[str, Any] | None]


class PbsRefreshLog(SharedEntity):
    __tablename__ = "pbs_refresh_log"
    __extra_args__ = (CheckConstraint("item_count IS NULL OR item_count >= 0", name="item_count"),)

    schedule_date: Mapped[date | None]
    refreshed_at: Mapped[datetime]
    item_count: Mapped[int | None]
    status: Mapped[str] = mapped_column(info=allowed(*REFRESH_STATUSES))
    error_detail: Mapped[str | None]
