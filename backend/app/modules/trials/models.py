"""Trial registry records, sites, snapshots and parsed criteria (design doc §6.3, §11)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import SharedEntity, allowed

REGISTRIES = ("CTGOV", "ANZCTR")
CRITERION_KINDS = ("inclusion", "exclusion")
CRITERION_SCOPES = ("target_condition", "whole_person")


class TrialSnapshot(SharedEntity):
    """An immutable registry snapshot, so Match Runs are reproducible."""

    __tablename__ = "trial_snapshot"
    __immutable__ = True
    __extra_args__ = (CheckConstraint("record_count >= 0", name="record_count"),)

    taken_at: Mapped[datetime]
    # "registry" is reserved by SQLAlchemy, so the attribute is named differently from the column.
    trial_registry: Mapped[str] = mapped_column("registry", info=allowed(*REGISTRIES))
    query_params: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    record_count: Mapped[int]


class Trial(SharedEntity):
    __tablename__ = "trial"
    __extra_args__ = (
        UniqueConstraint("registry", "external_id"),
        Index("ix_trial_conditions", "conditions", postgresql_using="gin"),
    )

    # "registry" is reserved by SQLAlchemy, so the attribute is named differently from the column.
    trial_registry: Mapped[str] = mapped_column("registry", info=allowed(*REGISTRIES))
    external_id: Mapped[str]
    title: Mapped[str]
    phase: Mapped[str | None]
    overall_status: Mapped[str | None]
    sponsor: Mapped[str | None]
    conditions: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    interventions: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trial_snapshot.id", ondelete="RESTRICT"), index=True
    )
    last_updated: Mapped[datetime | None]


class TrialSite(SharedEntity):
    __tablename__ = "trial_site"
    __extra_args__ = (Index("ix_trial_site_country_city", "country", "city"),)

    trial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trial.id", ondelete="RESTRICT"), index=True
    )
    facility: Mapped[str | None]
    city: Mapped[str | None]
    state: Mapped[str | None]
    country: Mapped[str | None]
    site_status: Mapped[str | None]
    lat: Mapped[Decimal | None]
    lng: Mapped[Decimal | None]
    # Computed from the Practice's location.
    travel_min: Mapped[int | None]


class TrialCriterion(SharedEntity):
    __tablename__ = "trial_criterion"

    trial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trial.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(info=allowed(*CRITERION_KINDS))
    raw_text: Mapped[str]
    # {attribute, operator, value}; the attribute comes from the owning module's vocabulary.
    structured: Mapped[dict[str, Any] | None]
    attribute: Mapped[str | None]
    category: Mapped[str | None]
    scope: Mapped[str] = mapped_column(info=allowed(*CRITERION_SCOPES))
    parser_version: Mapped[str | None]
