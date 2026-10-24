"""The Patient Summary's Diagnosis section (#47): its "last updated". The section itself is drawn by the frontend
from the Cancer Diagnoses, their Biomarkers and Recurrences."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.modules.clinical import conditions, entry
from app.modules.clinical.schemas import LastUpdated
from app.specialties.oncology import access, biomarkers, cancer_diagnoses, recurrences
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.models import Biomarker, CancerDiagnosis, Recurrence


def last_updated(db: Session, actor: Actor, patient_id: uuid.UUID) -> LastUpdated | None:
    access.require_view(db, actor, patient_id)
    condition_ids = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    diagnoses = list(db.scalars(select(CancerDiagnosis.id).where(CancerDiagnosis.condition_id.in_(condition_ids))))
    if not diagnoses:
        return None
    return entry.last_updated(db, actor.practice_id, {
        cancer_diagnoses.SUBJECT: diagnoses,
        biomarkers.SUBJECT: db.scalars(select(Biomarker.id).where(Biomarker.cancer_diagnosis_id.in_(diagnoses))),
        recurrences.SUBJECT: db.scalars(select(Recurrence.id).where(Recurrence.cancer_diagnosis_id.in_(diagnoses))),
    })
