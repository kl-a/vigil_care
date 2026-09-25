"""Patients (#8, design doc §5 screens 3–4). Developer admins are refused (403) by the service."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.crypto import Cipher
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.patients import service
from app.modules.patients.schemas import IdentityChange, NewPatient, PatientDetail, PatientRow

router = APIRouter(prefix="/patients", tags=["patients"])


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "No such Patient.")


@router.get("")
def list_patients(actor: SignedIn, db: Db, q: str | None = None) -> list[PatientRow]:
    return service.list_patients(db, actor, q)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_patient(new: NewPatient, actor: SignedIn, db: Db, cipher: Cipher) -> PatientDetail:
    return service.create_patient(db, cipher, actor, new)


@router.get("/{patient_id}")
def patient_detail(patient_id: uuid.UUID, actor: SignedIn, db: Db, cipher: Cipher) -> PatientDetail:
    try:
        return service.patient_detail(db, cipher, actor, patient_id)
    except service.PatientNotFound:
        raise _not_found() from None


@router.patch("/{patient_id}/identity")
def change_identity(patient_id: uuid.UUID, change: IdentityChange, actor: SignedIn, db: Db, cipher: Cipher) -> PatientDetail:
    try:
        return service.change_identity(db, cipher, actor, patient_id, change)
    except service.PatientNotFound:
        raise _not_found() from None
