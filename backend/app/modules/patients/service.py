"""Patients and Patient Identity (#8). Every User of the Practice sees its Patients; developer admins never do.

Identifying fields named in ENCRYPTED are AES-256-GCM ciphertext in `identity.patient_identity`, each sealed
to its field and Patient. Names, DOB and MRN stay searchable there, behind the `identity_access` role.
Changes are Verifications whose before/after are sealed too, so the audit spine never holds identity in
the clear.
"""

import base64
import json
import uuid
from typing import Any, NoReturn
from zoneinfo import ZoneInfo

from sqlalchemy import Select, or_, select, text
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.crypto import FieldCipher
from app.core.changes import blank_to_none, changed_fields
from app.core.permissions import require
from app.core.vocabulary import JOB_TITLE_LABEL
from app.modules.accounts.service import display_names
from app.modules.patients.models import Patient
from app.modules.patients.models import PatientIdentity
from app.modules.patients.schemas import (
    IdentityChange,
    IdentityHistoryEntry,
    NewPatient,
    IdentityDetails,
    PatientDetail,
    PatientRow,
)

PATIENT_SUBJECT = "patient"
ENCRYPTED = ("medicare_number", "ihi", "address", "phone", "mobile", "email", "next_of_kin_phone")
REQUIRED = ("given_name", "family_name")
PSEUDONYM_PREFIX = "VG-"


# Dates people read are the Practice's (Australia; one time zone until Sites span more than one).
PRACTICE_TIME_ZONE = ZoneInfo("Australia/Sydney")


class PatientNotFound(LookupError):
    """No such Patient in the actor's Practice."""


class PatientRemoved(LookupError):
    """The Patient was soft-deleted (#17): says who removed them, when and why."""


def field_context(field: str, patient_id: uuid.UUID) -> str:
    """What each encrypted field is sealed to: a ciphertext moved to another field or Patient won't open."""
    return f"patient_identity.{field}:{patient_id}"


def _audit_context(patient_id: uuid.UUID) -> str:
    return f"verification.patient:{patient_id}"


def _identity(cipher: FieldCipher, row: PatientIdentity) -> IdentityDetails:
    values: dict[str, Any] = {}
    for field in IdentityDetails.model_fields:
        if field in ENCRYPTED:
            sealed: bytes | None = getattr(row, f"{field}_encrypted")
            values[field] = cipher.decrypt(sealed, context=field_context(field, row.patient_id)) if sealed else None
        else:
            values[field] = getattr(row, field)
    return IdentityDetails(**values)


def _store(cipher: FieldCipher, row: PatientIdentity, field: str, value: Any) -> None:
    if field in ENCRYPTED:
        sealed = cipher.encrypt(value, context=field_context(field, row.patient_id)) if value else None
        setattr(row, f"{field}_encrypted", sealed)
    else:
        setattr(row, field, value)


def _seal(cipher: FieldCipher, patient_id: uuid.UUID, values: dict[str, Any] | None) -> dict[str, Any] | None:
    """Audit values, sealed. Which fields changed stays readable; their values don't."""
    if values is None:
        return None
    plaintext = json.dumps(values, default=str)
    sealed = cipher.encrypt(plaintext, context=_audit_context(patient_id))
    return {"fields": sorted(values), "sealed": base64.b64encode(sealed).decode()}


def _unseal(cipher: FieldCipher, patient_id: uuid.UUID, stored: dict[str, Any] | None) -> dict[str, Any] | None:
    if stored is None:
        return None
    values: dict[str, Any] = json.loads(cipher.decrypt(base64.b64decode(stored["sealed"]), context=_audit_context(patient_id)))
    return values


def display_name(identity: PatientIdentity | IdentityDetails) -> str:
    return f"{identity.given_name} {identity.family_name}"


def _patients(practice_id: uuid.UUID) -> Select[Patient, PatientIdentity]:
    return (
        select(Patient, PatientIdentity)
        .join(PatientIdentity, PatientIdentity.patient_id == Patient.id)
        .where(Patient.practice_id == practice_id)
    )


def _patient(db: Session, actor: Actor, patient_id: uuid.UUID) -> tuple[Patient, PatientIdentity]:
    row = db.execute(_patients(actor.practice_id).where(Patient.id == patient_id)).one_or_none()
    if row is None:
        _explain_missing(db, actor, patient_id)
    return row[0], row[1]


def _explain_missing(db: Session, actor: Actor, patient_id: uuid.UUID) -> NoReturn:
    removed = db.scalars(
        select(Patient)
        .where(Patient.id == patient_id, Patient.practice_id == actor.practice_id, Patient.deleted_at.is_not(None))
        .execution_options(include_deleted=True)
    ).one_or_none()
    if removed is None or removed.deleted_at is None:
        raise PatientNotFound()
    removal = next((e for e in audit.history(db, actor.practice_id, PATIENT_SUBJECT, patient_id) if e.action == "delete"), None)
    by = "someone"
    if removal is not None:
        name = display_names(db, {removal.user_id}).get(removal.user_id, "Unknown User")
        by = f"{name} ({JOB_TITLE_LABEL[removal.job_title_at_time]})"
    when = removed.deleted_at.astimezone(PRACTICE_TIME_ZONE).strftime("%-d %b %Y")
    raise PatientRemoved(f"This Patient was removed by {by} on {when}: {removed.deleted_reason}")


def _next_pseudonym(db: Session) -> str:
    number = db.scalar(text("SELECT nextval('patient_pseudonym_seq')"))
    return f"{PSEUDONYM_PREFIX}{number:04d}"


def list_patients(db: Session, actor: Actor, q: str | None = None) -> list[PatientRow]:
    """Every word of `q` matches a given or family name, or the start of the MRN."""
    require(actor.job_title, "view_patient_data")
    query = _patients(actor.practice_id)
    for word in (q or "").split():
        query = query.where(
            or_(
                PatientIdentity.given_name.ilike(f"%{word}%"),
                PatientIdentity.family_name.ilike(f"%{word}%"),
                PatientIdentity.mrn.ilike(f"{word}%"),
            )
        )
    rows = db.execute(query.order_by(PatientIdentity.family_name, PatientIdentity.given_name, Patient.pseudonym))
    return [
        PatientRow(
            id=patient.id,
            pseudonym=patient.pseudonym,
            display_name=display_name(identity),
            dob=identity.dob,
            mrn=identity.mrn,
            updated_at=max(patient.updated_at, identity.updated_at),
        )
        for patient, identity in rows
    ]


def patient_detail(db: Session, cipher: FieldCipher, actor: Actor, patient_id: uuid.UUID) -> PatientDetail:
    require(actor.job_title, "view_patient_data")
    patient, identity = _patient(db, actor, patient_id)
    entries = audit.history(db, actor.practice_id, PATIENT_SUBJECT, patient.id)
    names = display_names(db, {e.user_id for e in entries})
    history = [
        IdentityHistoryEntry(
            action=e.action,
            by_display_name=names.get(e.user_id, "Unknown User"),
            by_job_title=e.job_title_at_time,
            before=_unseal(cipher, patient.id, e.before),
            after=_unseal(cipher, patient.id, e.after),
            reason=e.reason,
            at=e.at,
        )
        for e in entries
    ]
    return PatientDetail(
        id=patient.id,
        pseudonym=patient.pseudonym,
        display_name=display_name(identity),
        identity=_identity(cipher, identity),
        history=history,
    )


def create_patient(db: Session, cipher: FieldCipher, actor: Actor, new: NewPatient) -> PatientDetail:
    require(actor.job_title, "verify_patient_identity")
    patient = Patient(practice_id=actor.practice_id, pseudonym=_next_pseudonym(db))
    db.add(patient)
    db.flush()
    identity = PatientIdentity(practice_id=actor.practice_id, patient_id=patient.id, given_name=new.given_name, family_name=new.family_name)
    values = blank_to_none(new.model_dump())
    for field, value in values.items():
        _store(cipher, identity, field, value)
    db.add(identity)
    db.flush()
    recorded = {field: value for field, value in values.items() if value is not None}
    audit.record_verification(
        db, actor, subject_table=PATIENT_SUBJECT, subject_id=patient.id, action="edit", after=_seal(cipher, patient.id, recorded)
    )
    return patient_detail(db, cipher, actor, patient.id)


def change_identity(db: Session, cipher: FieldCipher, actor: Actor, patient_id: uuid.UUID, change: IdentityChange) -> PatientDetail:
    require(actor.job_title, "verify_patient_identity")
    patient, identity = _patient(db, actor, patient_id)
    current = _identity(cipher, identity).model_dump()
    changed = changed_fields(current, change, required=REQUIRED)
    if changed:
        audit.record_verification(
            db, actor, subject_table=PATIENT_SUBJECT, subject_id=patient.id, action="edit",
            before=_seal(cipher, patient.id, {field: current[field] for field in changed}),
            after=_seal(cipher, patient.id, changed),
        )
        for field, value in changed.items():
            _store(cipher, identity, field, value)
        db.flush()
    return patient_detail(db, cipher, actor, patient.id)


def remove_patient(db: Session, actor: Actor, patient_id: uuid.UUID, reason: str) -> None:
    """Soft delete (#17): hidden from lists and search, never erased; the reason is on the Verification."""
    require(actor.job_title, "verify_patient_identity")
    patient, _ = _patient(db, actor, patient_id)
    audit.soft_delete(db, actor, patient, subject_table=PATIENT_SUBJECT, reason=reason)
