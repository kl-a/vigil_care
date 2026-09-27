"""The drug reference (#36) and the Medication Manager (#41). Refusals (403) come from the services."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.clinical import entry
from app.modules.medications import drug_reference, medications
from app.modules.medications.schemas import (
    DrugOption, MedicationChange, MedicationChangeRow, MedicationRow, NewMedication, Restart, Stop,
)

router = APIRouter(prefix="/drugs", tags=["medications"])


@router.get("")
def search_drugs(actor: SignedIn, db: Db, q: str = "") -> list[DrugOption]:
    """Drugs in the current PBS Schedule by generic or brand name, for picking a Medication."""
    return drug_reference.search(db, actor, q)


# --- The Medication Manager (#41) ------------------------------------------------------------------------

patients = APIRouter(prefix="/patients/{patient_id}", tags=["medications"])
_MISSING = (entry.PatientNotFound, entry.RecordNotFound)


def _refused(error: Exception) -> HTTPException:
    if isinstance(error, _MISSING):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Not found for this Patient.")
    if isinstance(error, medications.WrongStatus):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


_REFUSED = (*_MISSING, medications.WrongStatus, medications.InvalidMedication)


@patients.get("/medications")
def list_medications(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[MedicationRow]:
    """Most recently started first; the screen splits them into active and discontinued."""
    try:
        return medications.medications(db, actor, patient_id)
    except _REFUSED as error:
        raise _refused(error) from None


@patients.post("/medications", status_code=status.HTTP_201_CREATED)
def add_medication(patient_id: uuid.UUID, new: NewMedication, actor: SignedIn, db: Db) -> MedicationRow:
    try:
        return medications.add_medication(db, actor, patient_id, new)
    except _REFUSED as error:
        raise _refused(error) from None


@patients.patch("/medications/{medication_id}")
def change_medication(patient_id: uuid.UUID, medication_id: uuid.UUID, change: MedicationChange, actor: SignedIn, db: Db) -> MedicationRow:
    try:
        return medications.change_medication(db, actor, patient_id, medication_id, change)
    except _REFUSED as error:
        raise _refused(error) from None


@patients.post("/medications/{medication_id}/stop")
def stop_medication(patient_id: uuid.UUID, medication_id: uuid.UUID, stop: Stop, actor: SignedIn, db: Db) -> MedicationRow:
    """Discontinued from the date, and why. A Treatment Course it belongs to carries on."""
    try:
        return medications.stop_medication(db, actor, patient_id, medication_id, stop)
    except _REFUSED as error:
        raise _refused(error) from None


@patients.post("/medications/{medication_id}/restart")
def restart_medication(patient_id: uuid.UUID, medication_id: uuid.UUID, restart: Restart, actor: SignedIn, db: Db) -> MedicationRow:
    try:
        return medications.restart_medication(db, actor, patient_id, medication_id, restart)
    except _REFUSED as error:
        raise _refused(error) from None


@patients.delete("/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_medication(patient_id: uuid.UUID, medication_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        medications.remove_medication(db, actor, patient_id, medication_id, removal.reason)
    except _REFUSED as error:
        raise _refused(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@patients.get("/medication-changes")
def list_medication_changes(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[MedicationChangeRow]:
    """The change log: every change to the Patient's Medications, newest first."""
    try:
        return medications.change_log(db, actor, patient_id)
    except _REFUSED as error:
        raise _refused(error) from None
