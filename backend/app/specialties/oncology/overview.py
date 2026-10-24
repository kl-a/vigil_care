"""Oncology at a glance on the list screens (#57): the counts on its Clinical Data sub-tabs, and each Patient's
Cancer Types and Disease Extent on the Patient List."""

import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.permissions import require
from app.modules.clinical import conditions
from app.modules.clinical.conditions import condition_summaries
from app.specialties.oncology import access
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.models import Biomarker, CancerDiagnosis, CancerType, CnsStatus, PerformanceStatus, ResponseAssessment
from app.specialties.oncology.schemas import PatientListValues

# Most advanced first: the Patient List shows the most advanced of a Patient's Cancer Diagnoses.
EXTENT_ORDER = ("metastatic", "locally_advanced", "localised")
EXTENT_LABEL = {"metastatic": "Metastatic", "locally_advanced": "Locally advanced", "localised": "Localised"}


def oncology_counts(db: Session, actor: Actor, patient_id: uuid.UUID) -> dict[str, int]:
    """By sub-tab (its section id)."""
    access.require_view(db, actor, patient_id)
    practice = actor.practice_id
    ids = list(conditions.extended_conditions(db, practice, patient_id, MODULE_KEY))
    diagnoses = list(db.scalars(select(CancerDiagnosis.id).where(CancerDiagnosis.practice_id == practice, CancerDiagnosis.condition_id.in_(ids)))) if ids else []

    def count(model: type[ResponseAssessment] | type[PerformanceStatus] | type[CnsStatus]) -> int:
        return int(db.scalar(select(func.count()).select_from(model).where(model.practice_id == practice, model.patient_id == patient_id)) or 0)

    biomarkers = int(db.scalar(select(func.count()).select_from(Biomarker).where(Biomarker.practice_id == practice, Biomarker.cancer_diagnosis_id.in_(diagnoses))) or 0) if diagnoses else 0
    return {
        "cancer-diagnosis": len(diagnoses), "response-assessments": count(ResponseAssessment), "biomarkers": biomarkers,
        "performance-status": count(PerformanceStatus), "cns": count(CnsStatus),
    }


def patient_list_values(db: Session, actor: Actor) -> list[PatientListValues]:
    """For each of the Practice's Patients with a Cancer Diagnosis: its Cancer Types, and the most advanced Disease
    Extent. Only where Oncology is active."""
    require(actor.job_title, "view_patient_data")
    access.require_active(db, actor)
    cancers = {c.id: c.patient_id for c in condition_summaries(db, actor.practice_id, None) if c.extended_by_module == MODULE_KEY}
    if not cancers:
        return []
    rows = db.execute(
        select(CancerDiagnosis.condition_id, CancerType.display_name, CancerDiagnosis.disease_extent)
        .join(CancerType, CancerType.id == CancerDiagnosis.cancer_type_id)
        .where(CancerDiagnosis.practice_id == actor.practice_id, CancerDiagnosis.condition_id.in_(cancers))
        .order_by(CancerDiagnosis.dx_date.nulls_last(), CancerDiagnosis.created_at)
    )
    types: dict[uuid.UUID, list[str]] = defaultdict(list)
    extents: dict[uuid.UUID, set[str]] = defaultdict(set)
    for condition_id, cancer_type, extent in rows:
        patient = cancers[condition_id]
        if cancer_type not in types[patient]:
            types[patient].append(cancer_type)
        extents[patient].add(extent)
    return [
        PatientListValues(patient_id=patient, values={
            "cancer_types": names,
            "disease_extent": [EXTENT_LABEL[e] for e in EXTENT_ORDER if e in extents[patient]][:1],
        })
        for patient, names in types.items()
    ]
