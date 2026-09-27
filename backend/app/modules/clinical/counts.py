"""How many of each Clinical Record kind a Patient has (#57): the counts on the Clinical Data sub-tabs."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.modules.clinical import entry
from app.modules.clinical.models import ClinicalNote, Condition, ImagingStudy, LabResult, ManagementPlan, TreatmentCourse


def clinical_counts(db: Session, actor: Actor, patient_id: uuid.UUID) -> dict[str, int]:
    """By sub-tab: Conditions, Labs (tests, i.e. analytes, not results), Imaging Studies, Treatment Courses, and
    Management Plans and Clinical Notes."""
    entry.require_view(db, actor, patient_id)

    def count(query: object) -> int:
        return int(db.scalar(query) or 0)  # type: ignore[call-overload]

    practice, patient = actor.practice_id, patient_id
    return {
        "conditions": count(select(func.count()).select_from(Condition).where(Condition.practice_id == practice, Condition.patient_id == patient)),
        "labs": count(select(func.count(func.distinct(LabResult.analyte))).where(LabResult.practice_id == practice, LabResult.patient_id == patient)),
        "imaging": count(select(func.count()).select_from(ImagingStudy).where(ImagingStudy.practice_id == practice, ImagingStudy.patient_id == patient)),
        "treatment": count(
            select(func.count()).select_from(TreatmentCourse).join(Condition, Condition.id == TreatmentCourse.condition_id)
            .where(TreatmentCourse.practice_id == practice, Condition.patient_id == patient)
        ),
        "plan": count(select(func.count()).select_from(ManagementPlan).where(ManagementPlan.practice_id == practice, ManagementPlan.patient_id == patient))
        + count(select(func.count()).select_from(ClinicalNote).where(ClinicalNote.practice_id == practice, ClinicalNote.patient_id == patient)),
    }
