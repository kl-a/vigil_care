"""PBS Schedule items and Refresh history (design doc §6.3, §10.2)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SharedEntity, allowed
from app.core.vocabulary import REFRESH_STATUSES

RESTRICTION_LEVELS = (
    "unrestricted",
    "restricted",
    "authority_required",
    "authority_required_streamlined",
)
# Where a Refresh got the schedule: the PBS Schedule API, or the bundled sample (not for clinical use).
PBS_SOURCES = ("pbs_api", "sample")


class PbsRefreshLog(SharedEntity):
    __tablename__ = "pbs_refresh_log"
    __extra_args__ = (CheckConstraint("item_count IS NULL OR item_count >= 0", name="item_count"),)

    schedule_date: Mapped[date | None]
    refreshed_at: Mapped[datetime]
    item_count: Mapped[int | None]
    status: Mapped[str] = mapped_column(info=allowed(*REFRESH_STATUSES))
    source: Mapped[str] = mapped_column(info=allowed(*PBS_SOURCES))
    # The schedule's PBS Safety Net thresholds (patient spending in a calendar year).
    safety_net_general: Mapped[Decimal | None]
    safety_net_concessional: Mapped[Decimal | None]
    error_detail: Mapped[str | None]


class PbsItem(SharedEntity):
    __tablename__ = "pbs_item"
    __extra_args__ = (UniqueConstraint("item_code", "schedule_date"),)

    item_code: Mapped[str]
    drug_name: Mapped[str]
    brand_names: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    form: Mapped[str | None]
    program_code: Mapped[str | None]
    program_title: Mapped[str | None]
    # WHO ATC codes, e.g. ["N06BA02"]: their first letter is the therapeutic group.
    atc_codes: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    restriction_level: Mapped[str] = mapped_column(info=allowed(*RESTRICTION_LEVELS))
    # Per-indication restriction levels; PBS Listing per Condition is derived from these.
    # [{"indication", "treatment_phase", "level", "restriction_code", "conditions": [...]}]
    indications: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    # Per prescription: the most units (e.g. tablets) and packs; `pack_size` units come in a pack.
    max_quantity: Mapped[int | None]
    max_packs: Mapped[int | None]
    pack_size: Mapped[int | None]
    # Infusions are prescribed by amount (e.g. 200 mg), not by packs.
    max_amount: Mapped[Decimal | None]
    amount_unit: Mapped[str | None]
    repeats: Mapped[int | None]
    patient_copay_general: Mapped[Decimal | None]
    patient_copay_concessional: Mapped[Decimal | None]
    schedule_date: Mapped[date]
    # The Refresh that last loaded it: the lookup shows the items of the latest Refresh that loaded any.
    refresh_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pbs_refresh_log.id", ondelete="RESTRICT"), index=True
    )
    raw_data: Mapped[dict[str, Any] | None]
