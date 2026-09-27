"""The Medication Manager (#41, design doc §5 screen 10, §6.3, §15 Stage 4b): a Patient's Medications entered by
hand, following the Clinical Record's pattern (`clinical.entry`).

- A Medication is picked from the **drug reference** (its PBS Items open the PBS Drug Lookup) or typed as free
  text, "not in the drug reference".
- A cancer drug's Medication may link to its **Treatment Course**; stopping it changes the Medication only.
- Every change is written to the Medication's **change log** (who, when, why) and verified; a change after adding
  needs a reason, once per save. A Medication is discontinued only by stopping it, with the date and why.
"""

import uuid
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.database import INCLUDE_DELETED
from app.modules.accounts.service import display_names
from app.modules.clinical import entry
from app.modules.clinical.treatment_courses import CourseSummary, course_summaries
from app.modules.medications.models import DrugReference, Medication, MedicationChangeLog
from app.modules.medications.schemas import (
    ChangeType, MedicationChange, MedicationChangeRow, MedicationRow, MedicationStatus, NewMedication, Restart, Stop,
)
from app.modules.practice.providers import provider_names

FACT_KIND = "medication"
SUBJECT = "medication"
# Fields whose change is a dose change in the change log; any other change is a correction.
DOSE_FIELDS = {"dose_amount", "dose_unit", "frequency", "frequency_detail"}
STOPPED = ("discontinued", "completed")
# Hand-entered Medications are verified as they're entered.
ENTERED_CONFIDENCE = "high"


class InvalidMedication(ValueError):
    """Links to another Patient's course or another Practice's Provider, or dates out of order."""


class WrongStatus(ValueError):
    """Stopping a Medication already stopped, or restarting one that's still being taken."""


def _fields(med: Medication) -> dict[str, Any]:
    """The Medication as its Verifications and change log record it."""
    names = (
        "brand_name", "dose_amount", "dose_unit", "frequency", "frequency_detail", "route", "indication", "category", "start_date",
        "prescribed_by_provider_id", "treatment_course_id", "notes", "status", "end_date", "reason_discontinued",
    )
    return {name: entry.audit_value(getattr(med, name)) for name in names}


def _course_name(course: CourseSummary) -> str:
    return course.regimen_name or course.modality.capitalize()


def _dose(med: Medication) -> str | None:
    if med.dose_amount is None:
        return med.dose_display
    amount = f"{Decimal(med.dose_amount).normalize():f}"
    return f"{amount} {med.dose_unit}" if med.dose_unit else amount


def _rows(db: Session, actor: Actor, patient_id: uuid.UUID, meds: list[Medication]) -> list[MedicationRow]:
    drug_ids = {m.drug_reference_id for m in meds if m.drug_reference_id}
    drugs = {d.id: d for d in db.scalars(select(DrugReference).where(DrugReference.id.in_(drug_ids)))} if drug_ids else {}
    prescribers = provider_names(db, actor.practice_id, {m.prescribed_by_provider_id for m in meds if m.prescribed_by_provider_id}, include_removed=True)
    courses = {c.id: _course_name(c) for c in course_summaries(db, actor.practice_id, patient_id)}
    entered = entry.entered(db, actor.practice_id, SUBJECT, (m.id for m in meds))
    rows = []
    for m in meds:
        drug = drugs.get(m.drug_reference_id) if m.drug_reference_id else None
        rows.append(MedicationRow(
            id=m.id, drug_reference_id=m.drug_reference_id, drug_name=m.drug_name_raw, generic_name=m.generic_name,
            in_drug_reference=drug is not None, is_cancer_drug=bool(drug and drug.is_cancer_drug),
            pbs_item_codes=[str(code) for code in drug.pbs_item_codes] if drug else [],
            brand_name=m.brand_name, dose_amount=m.dose_amount, dose_unit=m.dose_unit, dose_display=_dose(m), frequency=m.frequency,  # type: ignore[arg-type]
            frequency_detail=m.frequency_detail, route=m.route, indication=m.indication, category=m.category,  # type: ignore[arg-type]
            start_date=m.start_date, end_date=m.end_date, status=cast(MedicationStatus, m.status), reason_discontinued=m.reason_discontinued,
            prescribed_by_provider_id=m.prescribed_by_provider_id, prescriber_name=prescribers.get(m.prescribed_by_provider_id) if m.prescribed_by_provider_id else None,
            treatment_course_id=m.treatment_course_id, treatment_course_name=courses.get(m.treatment_course_id) if m.treatment_course_id else None,
            notes=m.notes, source=m.source, entered=entered.get(m.id),
        ))
    return rows


def _check_links(db: Session, actor: Actor, patient_id: uuid.UUID, course_id: uuid.UUID | None, provider_id: uuid.UUID | None) -> None:
    if course_id and course_id not in {c.id for c in course_summaries(db, actor.practice_id, patient_id)}:
        raise InvalidMedication("No such Treatment Course for this Patient.")
    if provider_id and not provider_names(db, actor.practice_id, {provider_id}):
        raise InvalidMedication("No such Provider in this Practice.")


def _check_dates(med: Medication) -> None:
    if med.start_date and med.end_date and med.end_date < med.start_date:
        raise InvalidMedication("A Medication can't stop before it starts.")


def _log(
    db: Session, actor: Actor, med: Medication, change_type: ChangeType, previous: dict[str, Any] | None, new: dict[str, Any] | None,
    reason: str | None,
) -> None:
    db.add(MedicationChangeLog(
        practice_id=actor.practice_id, medication_id=med.id, change_type=change_type, previous_value=previous, new_value=new,
        changed_by_user_id=actor.id, reason=reason,
    ))
    db.flush()


def _live(db: Session, actor: Actor, patient_id: uuid.UUID, medication_id: uuid.UUID) -> Medication:
    return entry.live_row(db, actor, Medication, patient_id, medication_id)


def _one(db: Session, actor: Actor, patient_id: uuid.UUID, med: Medication) -> MedicationRow:
    db.flush()
    db.refresh(med)
    [row] = _rows(db, actor, patient_id, [med])
    return row


def medications(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[MedicationRow]:
    """Every live Medication, most recently started first."""
    entry.require_view(db, actor, patient_id)
    found = db.scalars(
        select(Medication)
        .where(Medication.practice_id == actor.practice_id, Medication.patient_id == patient_id)
        .order_by(Medication.start_date.desc().nulls_last(), Medication.created_at.desc())
    )
    return _rows(db, actor, patient_id, list(found))


def add_medication(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewMedication) -> MedicationRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    _check_links(db, actor, patient_id, new.treatment_course_id, new.prescribed_by_provider_id)
    values = new.model_dump(exclude={"drug_reference_id", "drug_name"})
    if new.drug_reference_id:
        drug = db.get(DrugReference, new.drug_reference_id)
        if drug is None:
            raise InvalidMedication("No such drug in the drug reference.")
        names = {"drug_reference_id": drug.id, "drug_name_raw": drug.generic_name, "generic_name": drug.generic_name}
    else:
        names = {"drug_name_raw": new.drug_name}
    med = Medication(patient_id=patient_id, confidence=ENTERED_CONFIDENCE, **entry.entered_by(actor), **names, **values)
    db.add(med)
    entry.record_added(db, actor, SUBJECT, med, _fields(med))
    _log(db, actor, med, "added", None, _fields(med), None)
    return _one(db, actor, patient_id, med)


def change_medication(db: Session, actor: Actor, patient_id: uuid.UUID, medication_id: uuid.UUID, change: MedicationChange) -> MedicationRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    med = _live(db, actor, patient_id, medication_id)
    _check_links(db, actor, patient_id, change.treatment_course_id, change.prescribed_by_provider_id)
    current = _fields(med)
    changed = entry.correct(db, actor, SUBJECT, med, current, change, change.reason)
    if changed:
        _check_dates(med)
        kind: ChangeType = "status_changed" if "status" in changed else "dose_changed" if set(changed) <= DOSE_FIELDS else "corrected"
        _log(db, actor, med, kind, {field: current[field] for field in changed}, changed, change.reason)
    return _one(db, actor, patient_id, med)


def _set_status(db: Session, actor: Actor, med: Medication, change_type: ChangeType, values: dict[str, Any], reason: str) -> None:
    before = _fields(med)
    for field, value in values.items():
        setattr(med, field, value)
    _check_dates(med)
    after = _fields(med)
    previous = {field: before[field] for field in values}
    new = {field: after[field] for field in values}
    audit.record_verification(db, actor, subject_table=SUBJECT, subject_id=med.id, action="edit", before=previous, after=new, reason=reason)
    _log(db, actor, med, change_type, previous, new, reason)


def stop_medication(db: Session, actor: Actor, patient_id: uuid.UUID, medication_id: uuid.UUID, stop: Stop) -> MedicationRow:
    """Discontinued from `end_date`, and why. Its Treatment Course, if any, carries on."""
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    med = _live(db, actor, patient_id, medication_id)
    if med.status in STOPPED:
        raise WrongStatus("This Medication is already stopped.")
    _set_status(db, actor, med, "discontinued", {"status": "discontinued", "end_date": stop.end_date, "reason_discontinued": stop.reason}, stop.reason)
    return _one(db, actor, patient_id, med)


def restart_medication(db: Session, actor: Actor, patient_id: uuid.UUID, medication_id: uuid.UUID, restart: Restart) -> MedicationRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    med = _live(db, actor, patient_id, medication_id)
    if med.status == "active":
        raise WrongStatus("This Medication is already being taken.")
    _set_status(db, actor, med, "restarted", {"status": "active", "end_date": None, "reason_discontinued": None}, restart.reason)
    return _one(db, actor, patient_id, med)


def remove_medication(db: Session, actor: Actor, patient_id: uuid.UUID, medication_id: uuid.UUID, reason: str) -> None:
    """Entered in error: removed (soft), and the change log says so."""
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    med = _live(db, actor, patient_id, medication_id)
    _log(db, actor, med, "corrected", _fields(med), None, reason)
    audit.soft_delete(db, actor, med, subject_table=SUBJECT, reason=reason, before=_fields(med))


def change_log(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[MedicationChangeRow]:
    """Every change to the Patient's Medications, removed ones included, newest first."""
    entry.require_view(db, actor, patient_id)
    found = db.execute(
        select(MedicationChangeLog, Medication.drug_name_raw)
        .join(Medication, Medication.id == MedicationChangeLog.medication_id)
        .where(MedicationChangeLog.practice_id == actor.practice_id, Medication.patient_id == patient_id)
        .order_by(MedicationChangeLog.changed_at.desc(), MedicationChangeLog.created_at.desc())
        .execution_options(**{INCLUDE_DELETED: True})
    ).all()
    names = display_names(db, {log.changed_by_user_id for log, _ in found})
    return [
        MedicationChangeRow(
            id=log.id, medication_id=log.medication_id, drug_name=drug_name, change_type=cast(ChangeType, log.change_type),
            previous_value=log.previous_value, new_value=log.new_value, by=names.get(log.changed_by_user_id, "Unknown User"),
            at=log.changed_at, reason=log.reason,
        )
        for log, drug_name in found
    ]
