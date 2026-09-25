"""Drug reference, Medications and their change log (design doc §6.3, §7.2)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import (
    PracticeEntity,
    Provenance,
    SharedEntity,
    allowed,
    practice_fk,
    provenance_args,
)
from app.core.vocabulary import CONFIDENCE_LEVELS

MEDICATION_STATUSES = ("active", "discontinued", "on_hold", "completed", "unknown")
FREQUENCIES = (
    "daily",
    "twice_daily",
    "three_times_daily",
    "weekly",
    "fortnightly",
    "monthly",
    "prn",
    "stat",
    "other",
)
ROUTES = ("oral", "iv", "subcut", "im", "topical", "inhaled", "pr", "other")
CATEGORIES = ("cancer_treatment", "supportive_care", "comorbidity_management", "supplement", "other")
SOURCES = ("patient_reported", "document_extracted", "doctor_entered", "pharmacy_list")
CHANGE_TYPES = (
    "added",
    "dose_changed",
    "discontinued",
    "restarted",
    "status_changed",
    "verified",
    "corrected",
)


class DrugReference(SharedEntity):
    __tablename__ = "drug_reference"
    __extra_args__ = (UniqueConstraint("generic_name"),)

    generic_name: Mapped[str]
    brand_names: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    drug_class: Mapped[str | None]
    atc_code: Mapped[str | None]
    is_cancer_drug: Mapped[bool] = mapped_column(server_default=text("false"))
    pbs_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pbs_item.id", ondelete="SET NULL"), index=True
    )
    common_doses: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    common_routes: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))


class Medication(PracticeEntity, Provenance):
    """Verification lives in `verification`, not on this row."""

    __tablename__ = "medication"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("treatment_course_id", "treatment_course"),
        practice_fk("prescribed_by_provider_id", "provider", ondelete="SET NULL"),
        *provenance_args(),
        CheckConstraint("dose_amount IS NULL OR dose_amount > 0", name="dose_positive"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates_ordered"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    drug_reference_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("drug_reference.id", ondelete="RESTRICT"), index=True
    )
    drug_name_raw: Mapped[str]
    generic_name: Mapped[str | None]
    brand_name: Mapped[str | None]
    dose_amount: Mapped[Decimal | None]
    dose_unit: Mapped[str | None]
    dose_display: Mapped[str | None]
    frequency: Mapped[str | None] = mapped_column(info=allowed(*FREQUENCIES))
    frequency_detail: Mapped[str | None]
    route: Mapped[str | None] = mapped_column(info=allowed(*ROUTES))
    indication: Mapped[str | None]
    category: Mapped[str | None] = mapped_column(info=allowed(*CATEGORIES))
    status: Mapped[str] = mapped_column(
        info=allowed(*MEDICATION_STATUSES), server_default=text("'unknown'")
    )
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    reason_discontinued: Mapped[str | None]
    prescribed_by_provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(info=allowed(*SOURCES))
    confidence: Mapped[str] = mapped_column(info=allowed(*CONFIDENCE_LEVELS))
    # Set when the drug belongs to a Treatment Course (e.g. one drug of a Regimen).
    treatment_course_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    notes: Mapped[str | None]


class MedicationChangeLog(PracticeEntity):
    """Never changes once written."""

    __tablename__ = "medication_change_log"
    __immutable__ = True
    __extra_args__ = (
        practice_fk("medication_id", "medication"),
        practice_fk("changed_by_user_id", "user"),
    )

    medication_id: Mapped[uuid.UUID] = mapped_column(index=True)
    change_type: Mapped[str] = mapped_column(info=allowed(*CHANGE_TYPES))
    previous_value: Mapped[dict[str, Any] | None]
    new_value: Mapped[dict[str, Any] | None]
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    changed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reason: Mapped[str | None]
