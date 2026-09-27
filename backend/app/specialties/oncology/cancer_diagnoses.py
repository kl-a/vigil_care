"""Cancer Types and Cancer Diagnosis (#37, design doc §6.3–6.4, §15 Stage 4a).

A primary cancer is a Condition (Core) that Oncology extends into a Cancer Diagnosis, with its Stage (at
diagnosis, never updated as the disease changes, only corrected) and Disease Extent (now). Clinicians only, and
only where Oncology is active: switched off, the module's tools go and its facts show read-only (ADR 0004).
Built on the Core's `entry` pattern: provenance, a Verification per change, a reason per correction.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import conditions, entry
from app.specialties.oncology import access, biomarkers
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.models import CancerDiagnosis, CancerType
from app.specialties.oncology.schemas import CancerDiagnosisChange, CancerDiagnosisRow, CancerTypeOption, NewCancerDiagnosis

FACT_KIND = "cancer_diagnosis"
SUBJECT = "cancer_diagnosis"
FIELDS = (
    "histology", "primary_site", "laterality", "dx_date", "stage_system", "stage", "disease_extent",
    "disease_extent_as_of", "cancer_status",
)


class UnknownCancerType(ValueError):
    """No such Cancer Type in the registry."""


def _option(cancer_type: CancerType) -> CancerTypeOption:
    return CancerTypeOption(
        key=cancer_type.key, display_name=cancer_type.display_name, mesh_term=cancer_type.mesh_term,
        mesh_id=cancer_type.mesh_id, staging_systems=[str(s) for s in cancer_type.staging_systems],
    )


def cancer_types(db: Session, actor: Actor) -> list[CancerTypeOption]:
    """The active Cancer Types, A–Z."""
    entry.require_patient_data(actor)
    access.require_active(db, actor)
    return [_option(t) for t in db.scalars(select(CancerType).where(CancerType.is_active).order_by(CancerType.display_name))]


def _fields(diagnosis: CancerDiagnosis) -> dict[str, Any]:
    """The Cancer Diagnosis as its Verifications record it (dates as text)."""
    return {f: entry.audit_value(getattr(diagnosis, f)) for f in FIELDS}


def _rows(db: Session, actor: Actor, patient_id: uuid.UUID, diagnoses: list[CancerDiagnosis]) -> list[CancerDiagnosisRow]:
    names = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    types = {t.id: t for t in db.scalars(select(CancerType).where(CancerType.id.in_({d.cancer_type_id for d in diagnoses})))}
    entered = entry.entered(db, actor.practice_id, SUBJECT, (d.id for d in diagnoses))
    chips = biomarkers.current_chips(db, actor.practice_id, (d.id for d in diagnoses))
    return [
        CancerDiagnosisRow(
            id=d.id, condition_id=d.condition_id, name=names.get(d.condition_id, ""), cancer_type=_option(types[d.cancer_type_id]),
            entered=entered.get(d.id), current_biomarkers=chips.get(d.id, []), **{f: getattr(d, f) for f in FIELDS},
        )
        for d in diagnoses
    ]


def cancer_diagnoses(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[CancerDiagnosisRow]:
    """By date of diagnosis (unknown last), then as entered."""
    access.require_view(db, actor, patient_id)
    ids = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    diagnoses = db.scalars(
        select(CancerDiagnosis)
        .where(CancerDiagnosis.practice_id == actor.practice_id, CancerDiagnosis.condition_id.in_(ids))
        .order_by(CancerDiagnosis.dx_date.asc().nulls_last(), CancerDiagnosis.created_at)
    )
    return _rows(db, actor, patient_id, list(diagnoses))


def record_cancer_diagnosis(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewCancerDiagnosis) -> CancerDiagnosisRow:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    cancer_type = db.scalars(select(CancerType).where(CancerType.key == new.cancer_type, CancerType.is_active)).one_or_none()
    if cancer_type is None:
        raise UnknownCancerType("No such Cancer Type.")
    condition = conditions.create_extended(db, actor, patient_id, MODULE_KEY, new.name or cancer_type.display_name)
    diagnosis = CancerDiagnosis(
        condition_id=condition.id, cancer_type_id=cancer_type.id, **entry.entered_by(actor),
        **new.model_dump(include=set(FIELDS)),
    )
    db.add(diagnosis)
    entry.record_added(db, actor, SUBJECT, diagnosis, {"cancer_type": cancer_type.key, **_fields(diagnosis)})
    [row] = _rows(db, actor, patient_id, [diagnosis])
    return row


def correct_cancer_diagnosis(
    db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID, change: CancerDiagnosisChange
) -> CancerDiagnosisRow:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    diagnosis = access.diagnosis_of(db, actor, patient_id, diagnosis_id)
    if change.name is not None:
        conditions.rename_extended(db, actor, diagnosis.condition_id, change.name, change.reason)
    entry.correct(
        db, actor, SUBJECT, diagnosis, _fields(diagnosis), change, change.reason,
        required=("disease_extent", "cancer_status"), exclude=("name",),
    )
    [row] = _rows(db, actor, patient_id, [diagnosis])
    return row


def remove_cancer_diagnosis(db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID, reason: str) -> None:
    """Removes the Cancer Diagnosis and the Condition it extends, each with the reason."""
    access.require_entry(db, actor, patient_id, FACT_KIND)
    diagnosis = access.diagnosis_of(db, actor, patient_id, diagnosis_id)
    audit.soft_delete(db, actor, diagnosis, subject_table=SUBJECT, reason=reason, before=_fields(diagnosis))
    conditions.remove_extended(db, actor, diagnosis.condition_id, reason)
