"""Core Clinical Record: Conditions, Treatment Courses, imaging, labs, plans and notes (design doc §6.3).

A row exists here only after a Verification (or direct entry by a User); candidates live in `extracted_fact`.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import PracticeEntity, Provenance, allowed, practice_fk, provenance_args
from app.core.vocabulary import TREATMENT_INTENTS

CONDITION_STATUSES = ("active", "resolved")
TREATMENT_MODALITIES = ("systemic", "surgery", "radiation")
LAB_FLAGS = ("low", "normal", "high", "critical")
NEXT_STEP_KINDS = ("rescan", "mdt", "trial_window", "review", "other")
NOTE_TYPES = ("clinical_note", "letter_to_referrer", "discharge_summary")


class Condition(PracticeEntity, Provenance):
    """Any diagnosed condition. Comorbidity is a view over this table, not a table."""

    __tablename__ = "condition"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        *provenance_args(),
        Index("ix_condition_patient_id_status", "patient_id", "status"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    name: Mapped[str]
    code_system: Mapped[str | None]
    code: Mapped[str | None]
    status: Mapped[str] = mapped_column(
        info=allowed(*CONDITION_STATUSES), server_default=text("'active'")
    )
    onset_date: Mapped[date | None]
    # The Specialty Module that extends this Condition (e.g. oncology → cancer_diagnosis).
    extended_by_module: Mapped[str | None] = mapped_column(
        ForeignKey("specialty_module.key", ondelete="RESTRICT"), index=True
    )
    notes: Mapped[str | None]


class TreatmentCourse(PracticeEntity, Provenance):
    __tablename__ = "treatment_course"
    __extra_args__ = (
        practice_fk("condition_id", "condition"),
        *provenance_args(),
        CheckConstraint(
            "modality = 'systemic' OR (regimen_name IS NULL AND regimen_planned IS NULL)",
            name="regimen_systemic_only",
        ),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates_ordered"),
        Index("ix_treatment_course_condition_id_start_date", "condition_id", "start_date"),
    )

    condition_id: Mapped[uuid.UUID] = mapped_column(index=True)
    modality: Mapped[str] = mapped_column(info=allowed(*TREATMENT_MODALITIES))
    intent: Mapped[str | None] = mapped_column(info=allowed(*TREATMENT_INTENTS))
    regimen_name: Mapped[str | None]
    regimen_planned: Mapped[dict[str, Any] | None]
    start_date: Mapped[date | None]
    # Null = ongoing; set only when a User records that the course ended.
    end_date: Mapped[date | None]
    reason_stopped: Mapped[str | None]
    details: Mapped[dict[str, Any] | None]


class ImagingStudy(PracticeEntity, Provenance):
    __tablename__ = "imaging_study"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        *provenance_args(),
        Index(
            "ix_imaging_study_patient_modality_date", "patient_id", "modality", text("study_date DESC")
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    modality: Mapped[str]
    body_region: Mapped[str | None]
    study_date: Mapped[date]
    impression: Mapped[str | None]
    comparison_date: Mapped[date | None]


class Finding(PracticeEntity, Provenance):
    """One observation in a single study; not linked across studies."""

    __tablename__ = "finding"
    __extra_args__ = (
        practice_fk("imaging_study_id", "imaging_study"),
        practice_fk("patient_id", "patient"),
        practice_fk("condition_id", "condition"),
        *provenance_args(),
        CheckConstraint("size_mm IS NULL OR size_mm > 0", name="size_positive"),
        CheckConstraint("suv_max IS NULL OR suv_max >= 0", name="suv_non_negative"),
    )

    imaging_study_id: Mapped[uuid.UUID] = mapped_column(index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Attributed only when the report says so.
    condition_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    site: Mapped[str | None]
    laterality: Mapped[str | None]
    description: Mapped[str]
    size_mm: Mapped[Decimal | None]
    suv_max: Mapped[Decimal | None]
    is_new: Mapped[bool | None]
    is_measurable: Mapped[bool | None]


class LabResult(PracticeEntity, Provenance):
    __tablename__ = "lab_result"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        *provenance_args(),
        CheckConstraint("num_nonnulls(value, value_text) >= 1", name="has_value"),
        Index("ix_lab_result_patient_analyte_collected", "patient_id", "analyte", text("collected_at DESC")),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    analyte: Mapped[str]
    value: Mapped[Decimal | None]
    # For results that aren't a plain number, e.g. "<5" or "positive".
    value_text: Mapped[str | None]
    unit: Mapped[str | None]
    ref_low: Mapped[Decimal | None]
    ref_high: Mapped[Decimal | None]
    flag: Mapped[str | None] = mapped_column(info=allowed(*LAB_FLAGS))
    collected_at: Mapped[datetime]
    panel: Mapped[str | None]


class ManagementPlan(PracticeEntity, Provenance):
    """Quoted verbatim; Vigil never rewrites it."""

    __tablename__ = "management_plan"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("authored_by_provider_id", "provider", ondelete="SET NULL"),
        *provenance_args(),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    plan_text: Mapped[str]
    plan_date: Mapped[date | None]
    authored_by_provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)


class NextStep(PracticeEntity):
    """Added by a User alongside the Management Plan; not extracted, so no provenance."""

    __tablename__ = "next_step"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("created_by_user_id", "user"),
        practice_fk("done_by_user_id", "user"),
        CheckConstraint("(done_at IS NULL) = (done_by_user_id IS NULL)", name="done_together"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(info=allowed(*NEXT_STEP_KINDS))
    description: Mapped[str]
    due_date: Mapped[date | None]
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    done_at: Mapped[datetime | None]
    done_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True)


class ClinicalNote(PracticeEntity, Provenance):
    __tablename__ = "clinical_note"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("author_provider_id", "provider", ondelete="SET NULL"),
        practice_fk("recipient_provider_id", "provider", ondelete="SET NULL"),
        *provenance_args(),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    note_type: Mapped[str] = mapped_column(info=allowed(*NOTE_TYPES))
    author_provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    recipient_provider_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    note_date: Mapped[date | None]
    content_summary: Mapped[str | None]
    key_points: Mapped[list[Any] | None]
