"""Oncology module tables (design doc §4.1, §6.3). They may reference Core tables; the Core never references them.

Each concept (Cancer Diagnosis, Recurrence, Biomarker, Line of Therapy, Response Assessment, ...) is a
self-contained unit, so it can move to another module or into the Core (portability rule).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import (
    PracticeEntity,
    Provenance,
    SharedEntity,
    allowed,
    member_fk,
    practice_fk,
    provenance_args,
)
from app.core.vocabulary import REFRESH_STATUSES, TREATMENT_INTENTS

DISEASE_EXTENTS = ("localised", "locally_advanced", "metastatic", "unknown")
CANCER_STATUSES = ("active", "no_evidence_of_disease", "unknown")
RECURRENCE_STATUSES = ("suspected", "confirmed", "reclassified_as_new_primary")
RECURRENCE_EXTENTS = ("local", "regional", "distant")
BIOMARKER_METHODS = ("NGS", "FISH", "IHC", "PCR", "ctDNA")
SPECIMEN_KINDS = ("primary", "metastasis", "liquid_biopsy")
BEST_RESPONSES = ("CR", "PR", "SD", "PD", "NE")
RESPONSE_DIRECTIONS = ("responding", "stable", "progressing")
RESPONSE_SOURCES = ("radiology_report", "clinician")
PERFORMANCE_SCALES = ("ECOG", "KPS")
PROTOCOL_DRUG_ROLES = ("backbone", "combination", "maintenance")


class CancerType(SharedEntity):
    """Site + histology only; no subtypes (they're derived from Biomarkers)."""

    __tablename__ = "cancer_type"
    __extra_args__ = (UniqueConstraint("key"),)

    key: Mapped[str]
    display_name: Mapped[str]
    icd10_codes: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    staging_systems: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))


class CancerDiagnosis(PracticeEntity, Provenance):
    """Oncology's 1:1 extension of a Condition that is a primary cancer."""

    __tablename__ = "cancer_diagnosis"
    __extra_args__ = (
        UniqueConstraint("condition_id"),
        practice_fk("condition_id", "condition"),
        *provenance_args(),
    )

    condition_id: Mapped[uuid.UUID]
    cancer_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cancer_type.id", ondelete="RESTRICT"), index=True
    )
    histology: Mapped[str | None]
    primary_site: Mapped[str | None]
    laterality: Mapped[str | None]
    dx_date: Mapped[date | None]
    stage_system: Mapped[str | None]
    # At diagnosis; never updated afterwards.
    stage: Mapped[str | None]
    disease_extent: Mapped[str] = mapped_column(
        info=allowed(*DISEASE_EXTENTS), server_default=text("'unknown'")
    )
    disease_extent_as_of: Mapped[date | None]
    cancer_status: Mapped[str] = mapped_column(
        info=allowed(*CANCER_STATUSES), server_default=text("'unknown'")
    )


class Recurrence(PracticeEntity, Provenance):
    __tablename__ = "recurrence"
    __extra_args__ = (
        practice_fk("cancer_diagnosis_id", "cancer_diagnosis"),
        practice_fk("evidence_document_id", "document"),
        member_fk("attributed_by_user_id"),
        practice_fk("new_cancer_diagnosis_id", "cancer_diagnosis"),
        *provenance_args(),
        CheckConstraint(
            "(attributed_by_user_id IS NULL) = (attributed_at IS NULL)", name="attributed_together"
        ),
        CheckConstraint(
            "status = 'suspected' OR attributed_by_user_id IS NOT NULL",
            name="attributed_unless_suspected",
        ),
        CheckConstraint(
            "(status = 'reclassified_as_new_primary') = (new_cancer_diagnosis_id IS NOT NULL)",
            name="new_primary_when_reclassified",
        ),
    )

    cancer_diagnosis_id: Mapped[uuid.UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(
        info=allowed(*RECURRENCE_STATUSES), server_default=text("'suspected'")
    )
    detected_on: Mapped[date | None]
    extent: Mapped[str | None] = mapped_column(info=allowed(*RECURRENCE_EXTENTS))
    sites: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    attributed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    attributed_at: Mapped[datetime | None]
    new_cancer_diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(index=True)


class Biomarker(PracticeEntity, Provenance):
    """Never overwritten. "Current" = latest `collected_on` per `name`."""

    __tablename__ = "biomarker"
    __extra_args__ = (
        practice_fk("cancer_diagnosis_id", "cancer_diagnosis"),
        *provenance_args(),
        Index("ix_biomarker_latest", "cancer_diagnosis_id", "name", text("collected_on DESC")),
    )

    cancer_diagnosis_id: Mapped[uuid.UUID] = mapped_column(index=True)
    name: Mapped[str]
    variant: Mapped[str | None]
    result: Mapped[str | None]
    value_num: Mapped[Decimal | None]
    value_unit: Mapped[str | None]
    method: Mapped[str | None] = mapped_column(info=allowed(*BIOMARKER_METHODS))
    specimen_site: Mapped[str | None]
    specimen_kind: Mapped[str | None] = mapped_column(info=allowed(*SPECIMEN_KINDS))
    collected_on: Mapped[date | None]
    reported_on: Mapped[date | None]


class OncologyCourseDetail(PracticeEntity, Provenance):
    """Oncology's 1:1 extension of a Treatment Course.

    Line of Therapy rule: `line_of_therapy` may be set only when the Treatment Course is systemic with
    palliative intent. It spans two tables, so a constraint trigger in the migration enforces it.
    """

    __tablename__ = "oncology_course_detail"
    __extra_args__ = (
        UniqueConstraint("treatment_course_id"),
        practice_fk("treatment_course_id", "treatment_course"),
        *provenance_args(),
        CheckConstraint("line_of_therapy IS NULL OR line_of_therapy >= 1", name="line_positive"),
    )

    treatment_course_id: Mapped[uuid.UUID]
    line_of_therapy: Mapped[int | None]
    treatment_protocol_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("treatment_protocol.id", ondelete="SET NULL"), index=True
    )
    best_response: Mapped[str | None] = mapped_column(info=allowed(*BEST_RESPONSES))


class ResponseAssessment(PracticeEntity, Provenance):
    __tablename__ = "response_assessment"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        practice_fk("cancer_diagnosis_id", "cancer_diagnosis"),
        practice_fk("imaging_study_id", "imaging_study"),
        practice_fk("overrides_id", "response_assessment"),
        *provenance_args(),
        CheckConstraint("overrides_id IS NULL OR source = 'clinician'", name="override_by_clinician"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Null = unattributed; shown as Needs Information.
    cancer_diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    assessed_on: Mapped[date]
    direction: Mapped[str] = mapped_column(info=allowed(*RESPONSE_DIRECTIONS))
    source: Mapped[str] = mapped_column(info=allowed(*RESPONSE_SOURCES))
    imaging_study_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    overrides_id: Mapped[uuid.UUID | None] = mapped_column(index=True)


class PerformanceStatus(PracticeEntity, Provenance):
    __tablename__ = "performance_status"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        *provenance_args(),
        CheckConstraint(
            "(scale = 'ECOG' AND value BETWEEN 0 AND 5)"
            " OR (scale = 'KPS' AND value BETWEEN 0 AND 100 AND value % 10 = 0)",
            name="value_in_scale",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    scale: Mapped[str] = mapped_column(info=allowed(*PERFORMANCE_SCALES))
    value: Mapped[int]
    assessed_on: Mapped[date]


class CnsStatus(PracticeEntity, Provenance):
    """First-class because CNS disease gates most oncology trials."""

    __tablename__ = "cns_status"
    __extra_args__ = (
        practice_fk("patient_id", "patient"),
        *provenance_args(),
        CheckConstraint("lesion_count IS NULL OR lesion_count >= 0", name="lesion_count"),
        CheckConstraint("steroid_dose_mg IS NULL OR steroid_dose_mg >= 0", name="steroid_dose"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(index=True)
    present: Mapped[bool | None]
    lesion_count: Mapped[int | None]
    locations: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    treated: Mapped[bool | None]
    treatment_type: Mapped[str | None]
    symptomatic: Mapped[bool | None]
    on_steroids: Mapped[bool | None]
    steroid_dose_mg: Mapped[Decimal | None]
    leptomeningeal: Mapped[bool | None]
    assessed_on: Mapped[date]


class TreatmentProtocol(SharedEntity):
    """An eviQ standard-of-care protocol."""

    __tablename__ = "treatment_protocol"
    __extra_args__ = (
        CheckConstraint("line_of_therapy IS NULL OR line_of_therapy >= 1", name="line_positive"),
    )

    cancer_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cancer_type.id", ondelete="RESTRICT"), index=True
    )
    protocol_name: Mapped[str]
    intent: Mapped[str | None] = mapped_column(info=allowed(*TREATMENT_INTENTS))
    line_of_therapy: Mapped[int | None]
    disease_extent_required: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    biomarker_requirements: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    eviq_id: Mapped[str | None]
    eviq_url: Mapped[str | None]
    eviq_version: Mapped[str | None]
    eviq_updated_on: Mapped[date | None]
    last_checked_at: Mapped[datetime | None]
    evidence_level: Mapped[str | None]
    raw_data: Mapped[dict[str, Any] | None]


class ProtocolDrug(SharedEntity):
    __tablename__ = "protocol_drug"

    treatment_protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("treatment_protocol.id", ondelete="RESTRICT"), index=True
    )
    drug_name: Mapped[str]
    generic_name: Mapped[str | None]
    role: Mapped[str | None] = mapped_column(info=allowed(*PROTOCOL_DRUG_ROLES))
    route: Mapped[str | None]
    pbs_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pbs_item.id", ondelete="SET NULL"), index=True
    )


class EviqRefreshLog(SharedEntity):
    __tablename__ = "eviq_refresh_log"
    __extra_args__ = (CheckConstraint("item_count IS NULL OR item_count >= 0", name="item_count"),)

    refreshed_at: Mapped[datetime]
    item_count: Mapped[int | None]
    status: Mapped[str] = mapped_column(info=allowed(*REFRESH_STATUSES))
    error_detail: Mapped[str | None]
