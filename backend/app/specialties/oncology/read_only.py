"""Oncology's facts in plain words, for when the module is inactive at a Practice (ADR 0004, amended): the
Core shows them read-only so a clinician never loses sight of a recorded cancer. Reached only through the
module contract's `read_only_view`, after the Core has checked the viewer may see the Patient."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clinical.conditions import extended_conditions
from app.specialties.oncology.models import CancerDiagnosis

MODULE_KEY = "oncology"


def _when(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def _line(name: str, diagnosis: CancerDiagnosis) -> str:
    """e.g. "Breast cancer: Stage IIA (TNM) at diagnosis, 1 Mar 2024; metastatic"."""
    parts = []
    if diagnosis.stage:
        system = f" ({diagnosis.stage_system})" if diagnosis.stage_system else ""
        when = f", {_when(diagnosis.dx_date)}" if diagnosis.dx_date else ""
        parts.append(f"Stage {diagnosis.stage}{system} at diagnosis{when}")
    elif diagnosis.dx_date:
        parts.append(f"diagnosed {_when(diagnosis.dx_date)}")
    if diagnosis.disease_extent != "unknown":
        parts.append(diagnosis.disease_extent.replace("_", " "))
    return f"{name}: {'; '.join(parts)}" if parts else name


def plain_facts(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[str]:
    """One line per Cancer Diagnosis."""
    names = extended_conditions(db, practice_id, patient_id, MODULE_KEY)
    if not names:
        return []
    diagnoses = db.scalars(
        select(CancerDiagnosis)
        .where(CancerDiagnosis.practice_id == practice_id, CancerDiagnosis.condition_id.in_(names))
        .order_by(CancerDiagnosis.dx_date, CancerDiagnosis.created_at)
    )
    return [_line(names[diagnosis.condition_id], diagnosis) for diagnosis in diagnoses]
