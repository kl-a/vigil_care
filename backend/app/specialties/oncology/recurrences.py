"""Recurrences (#39, design doc §6.3–6.4, §15 Stage 4a).

A clinician or trial coordinator records a **Suspected Recurrence** of a Cancer Diagnosis. Only a clinician
resolves it (`recurrence_attribution`, §6.4 row 4): **confirm** it, record a **new primary instead** (a new
Cancer Diagnosis; the Recurrence then points to it), or **rule it out** with a reason. Until then it stays an
Open Item (Stage 5).
"""

import uuid
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.accounts.service import display_names
from app.modules.clinical import conditions, entry
from app.specialties.oncology import access
from app.specialties.oncology.access import MODULE_KEY
from app.specialties.oncology.cancer_diagnoses import record_cancer_diagnosis
from app.specialties.oncology.models import CancerDiagnosis, Recurrence
from app.specialties.oncology.schemas import (
    NewCancerDiagnosis, NewRecurrence, RecurrenceExtent, RecurrenceRow, RecurrenceStatus, Resolved,
)

FACT_KIND = "recurrence"
RESOLVE_FACT_KIND = "recurrence_attribution"
SUBJECT = "recurrence"


class NotSuspected(ValueError):
    """Only a Suspected Recurrence is resolved."""


def _fields(recurrence: Recurrence) -> dict[str, Any]:
    return {
        "detected_on": entry.audit_value(recurrence.detected_on), "extent": recurrence.extent, "sites": list(recurrence.sites),
        "status": recurrence.status,
    }


def _rows(db: Session, actor: Actor, patient_id: uuid.UUID, recurrences: list[Recurrence]) -> list[RecurrenceRow]:
    names = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    # Each Cancer Diagnosis's name: the name of the Condition it extends.
    diagnosis_names = {
        d.id: names[d.condition_id] for d in db.scalars(select(CancerDiagnosis).where(CancerDiagnosis.condition_id.in_(names)))
    }
    resolvers = display_names(db, {r.attributed_by_user_id for r in recurrences if r.attributed_by_user_id})
    entered = entry.entered(db, actor.practice_id, SUBJECT, (r.id for r in recurrences))
    return [
        RecurrenceRow(
            id=r.id, cancer_diagnosis_id=r.cancer_diagnosis_id, cancer_diagnosis_name=diagnosis_names.get(r.cancer_diagnosis_id, ""),
            status=cast(RecurrenceStatus, r.status), detected_on=r.detected_on, extent=cast(RecurrenceExtent | None, r.extent),
            sites=[str(site) for site in r.sites], new_cancer_diagnosis_id=r.new_cancer_diagnosis_id,
            resolved=Resolved(by=resolvers.get(r.attributed_by_user_id, "Unknown User"), at=r.attributed_at)
            if r.attributed_by_user_id and r.attributed_at else None,
            ruled_out_reason=_ruled_out_reason(db, actor, r) if r.status == "ruled_out" else None,
            entered=entered.get(r.id),
        )
        for r in recurrences
    ]


def _ruled_out_reason(db: Session, actor: Actor, recurrence: Recurrence) -> str | None:
    return next((h.reason for h in audit.history(db, actor.practice_id, SUBJECT, recurrence.id) if h.action == "reject"), None)


def _live(db: Session, actor: Actor, patient_id: uuid.UUID, recurrence_id: uuid.UUID) -> Recurrence:
    """One of the Patient's live Recurrences (its Cancer Diagnosis is the Patient's)."""
    names = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    recurrence = db.scalars(
        select(Recurrence)
        .join(CancerDiagnosis, CancerDiagnosis.id == Recurrence.cancer_diagnosis_id)
        .where(Recurrence.id == recurrence_id, Recurrence.practice_id == actor.practice_id, CancerDiagnosis.condition_id.in_(names))
    ).one_or_none()
    if recurrence is None:
        raise entry.RecordNotFound()
    return recurrence


def recurrences(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[RecurrenceRow]:
    """Every Recurrence of the Patient's Cancer Diagnoses, most recently detected first."""
    access.require_view(db, actor, patient_id)
    names = conditions.extended_conditions(db, actor.practice_id, patient_id, MODULE_KEY)
    found = db.scalars(
        select(Recurrence)
        .join(CancerDiagnosis, CancerDiagnosis.id == Recurrence.cancer_diagnosis_id)
        .where(Recurrence.practice_id == actor.practice_id, CancerDiagnosis.condition_id.in_(names))
        .order_by(Recurrence.detected_on.desc().nulls_last(), Recurrence.created_at.desc())
    )
    return _rows(db, actor, patient_id, list(found))


def suspect(db: Session, actor: Actor, patient_id: uuid.UUID, diagnosis_id: uuid.UUID, new: NewRecurrence) -> RecurrenceRow:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    diagnosis = access.diagnosis_of(db, actor, patient_id, diagnosis_id)
    recurrence = Recurrence(cancer_diagnosis_id=diagnosis.id, status="suspected", **entry.entered_by(actor), **new.model_dump())
    db.add(recurrence)
    entry.record_added(db, actor, SUBJECT, recurrence, _fields(recurrence))
    [row] = _rows(db, actor, patient_id, [recurrence])
    return row


def _suspected(recurrence: Recurrence) -> Recurrence:
    if recurrence.status != "suspected":
        raise NotSuspected("Only a Suspected Recurrence can be resolved.")
    return recurrence


def _resolve(
    db: Session, actor: Actor, patient_id: uuid.UUID, recurrence_id: uuid.UUID, status: str, action: Any, reason: str | None = None,
    new_cancer_diagnosis_id: uuid.UUID | None = None,
) -> RecurrenceRow:
    recurrence = _suspected(_live(db, actor, patient_id, recurrence_id))
    audit.record_verification(
        db, actor, subject_table=SUBJECT, subject_id=recurrence.id, action=action,
        before={"status": "suspected"}, after={"status": status}, reason=reason,
    )
    recurrence.status, recurrence.attributed_by_user_id, recurrence.attributed_at = status, actor.id, func.now()
    recurrence.new_cancer_diagnosis_id = new_cancer_diagnosis_id
    db.flush()
    db.refresh(recurrence)
    [row] = _rows(db, actor, patient_id, [recurrence])
    return row


def confirm(db: Session, actor: Actor, patient_id: uuid.UUID, recurrence_id: uuid.UUID) -> RecurrenceRow:
    access.require_entry(db, actor, patient_id, RESOLVE_FACT_KIND)
    return _resolve(db, actor, patient_id, recurrence_id, "confirmed", "attribute")


def new_primary_instead(
    db: Session, actor: Actor, patient_id: uuid.UUID, recurrence_id: uuid.UUID, new: NewCancerDiagnosis
) -> RecurrenceRow:
    """Records the new Cancer Diagnosis, then points the Recurrence at it."""
    access.require_entry(db, actor, patient_id, RESOLVE_FACT_KIND)
    _suspected(_live(db, actor, patient_id, recurrence_id))
    created = record_cancer_diagnosis(db, actor, patient_id, new)
    return _resolve(db, actor, patient_id, recurrence_id, "reclassified_as_new_primary", "attribute", new_cancer_diagnosis_id=created.id)


def rule_out(db: Session, actor: Actor, patient_id: uuid.UUID, recurrence_id: uuid.UUID, reason: str) -> RecurrenceRow:
    access.require_entry(db, actor, patient_id, RESOLVE_FACT_KIND)
    return _resolve(db, actor, patient_id, recurrence_id, "ruled_out", "reject", reason=reason)


def remove(db: Session, actor: Actor, patient_id: uuid.UUID, recurrence_id: uuid.UUID, reason: str) -> None:
    access.require_entry(db, actor, patient_id, FACT_KIND)
    recurrence = _live(db, actor, patient_id, recurrence_id)
    audit.soft_delete(db, actor, recurrence, subject_table=SUBJECT, reason=reason, before=_fields(recurrence))


def plain_lines(db: Session, practice_id: uuid.UUID, diagnosis_id: uuid.UUID, name: str, when: Any) -> list[str]:
    """For the read-only view, e.g. "Breast cancer: suspected recurrence (distant: liver), 10 Feb 2026"."""
    found = db.scalars(
        select(Recurrence).where(Recurrence.practice_id == practice_id, Recurrence.cancer_diagnosis_id == diagnosis_id)
        .order_by(Recurrence.detected_on.desc().nulls_last())
    )
    lines = []
    for r in found:
        status = {"suspected": "suspected recurrence", "confirmed": "recurrence", "ruled_out": "recurrence ruled out",
                  "reclassified_as_new_primary": "new primary (was a suspected recurrence)"}[r.status]
        where = f" ({r.extent}: {', '.join(str(s) for s in r.sites)})" if r.extent or r.sites else ""
        lines.append(f"{name}: {status}{where}{', ' + when(r.detected_on) if r.detected_on else ''}")
    return lines
