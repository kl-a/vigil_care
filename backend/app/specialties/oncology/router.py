"""Oncology's API (#37): Cancer Types and Cancer Diagnoses. Mounted through the module contract; the services
refuse (403) Practices where Oncology isn't active, and anyone whose Job Title can't do it."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.clinical import entry
from app.specialties.oncology import cancer_diagnoses
from app.specialties.oncology.schemas import CancerDiagnosisChange, CancerDiagnosisRow, CancerTypeOption, NewCancerDiagnosis

router = APIRouter(tags=["oncology"])
_MISSING = (entry.PatientNotFound, entry.RecordNotFound)


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Not found for this Patient.")


@router.get("/cancer-types")
def cancer_types(actor: SignedIn, db: Db) -> list[CancerTypeOption]:
    return cancer_diagnoses.cancer_types(db, actor)


@router.get("/patients/{patient_id}/cancer-diagnoses")
def list_cancer_diagnoses(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[CancerDiagnosisRow]:
    try:
        return cancer_diagnoses.cancer_diagnoses(db, actor, patient_id)
    except _MISSING:
        raise _not_found() from None


@router.post("/patients/{patient_id}/cancer-diagnoses", status_code=status.HTTP_201_CREATED)
def record_cancer_diagnosis(patient_id: uuid.UUID, new: NewCancerDiagnosis, actor: SignedIn, db: Db) -> CancerDiagnosisRow:
    try:
        return cancer_diagnoses.record_cancer_diagnosis(db, actor, patient_id, new)
    except _MISSING:
        raise _not_found() from None
    except cancer_diagnoses.UnknownCancerType as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from None


@router.patch("/patients/{patient_id}/cancer-diagnoses/{diagnosis_id}")
def correct_cancer_diagnosis(
    patient_id: uuid.UUID, diagnosis_id: uuid.UUID, change: CancerDiagnosisChange, actor: SignedIn, db: Db
) -> CancerDiagnosisRow:
    try:
        return cancer_diagnoses.correct_cancer_diagnosis(db, actor, patient_id, diagnosis_id, change)
    except _MISSING:
        raise _not_found() from None


@router.delete("/patients/{patient_id}/cancer-diagnoses/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cancer_diagnosis(patient_id: uuid.UUID, diagnosis_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        cancer_diagnoses.remove_cancer_diagnosis(db, actor, patient_id, diagnosis_id, removal.reason)
    except _MISSING:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
