"""Access to Oncology's Clinical Record: the Core's rules (`clinical.entry`: Patient data, Verification Rights),
and only where Oncology is active for the Practice (ADR 0004: switched off, its facts stay visible read-only
through the Core's view, but its screens and endpoints close)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.permissions import NotAllowed
from app.modules.clinical import conditions, entry
from app.modules.registry.service import active_module_keys
from app.specialties.oncology.models import CancerDiagnosis

MODULE_KEY = "oncology"


def require_active(db: Session, actor: Actor) -> None:
    if MODULE_KEY not in active_module_keys(db, actor.practice_id):
        raise NotAllowed("Oncology isn't active at this Practice.")


def require_view(db: Session, actor: Actor, patient_id: uuid.UUID) -> None:
    entry.require_view(db, actor, patient_id)
    require_active(db, actor)


def require_entry(db: Session, actor: Actor, patient_id: uuid.UUID, fact_kind: str) -> None:
    entry.require_entry(db, actor, patient_id, fact_kind)
    require_active(db, actor)


def diagnosis_of(db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID) -> CancerDiagnosis:
    """The Patient's live Cancer Diagnosis (its Condition belongs to the Patient)."""
    ids = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    diagnosis = db.scalars(
        select(CancerDiagnosis).where(
            CancerDiagnosis.id == diagnosis_id, CancerDiagnosis.practice_id == actor.practice_id, CancerDiagnosis.condition_id.in_(ids)
        )
    ).one_or_none()
    if diagnosis is None:
        raise entry.RecordNotFound()
    return diagnosis
