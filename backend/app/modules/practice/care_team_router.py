"""Care Team (#9): on a Patient, and a Provider's Patients. Refusals (403) come from the service."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.practice import care_team
from app.modules.practice.schemas import CareTeamChange, CareTeamRow, NewCareTeamMember, ProviderPatientRow

router = APIRouter(tags=["care team"])

_STATUS: dict[type[Exception], tuple[int, str | None]] = {
    care_team.PatientNotFound: (status.HTTP_404_NOT_FOUND, "No such Patient."),
    care_team.MemberNotFound: (status.HTTP_404_NOT_FOUND, "No such Care Team member."),
    care_team.ProviderNotFound: (status.HTTP_404_NOT_FOUND, "No such Provider."),
    care_team.NoSuchProvider: (status.HTTP_422_UNPROCESSABLE_CONTENT, None),
    care_team.EndsBeforeItStarts: (status.HTTP_422_UNPROCESSABLE_CONTENT, None),
}


def _refused(error: Exception) -> HTTPException:
    code, message = _STATUS[type(error)]
    return HTTPException(code, message or str(error))


@router.get("/patients/{patient_id}/care-team")
def patient_care_team(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[CareTeamRow]:
    try:
        return care_team.care_team(db, actor, patient_id)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.post("/patients/{patient_id}/care-team", status_code=status.HTTP_201_CREATED)
def add_member(patient_id: uuid.UUID, new: NewCareTeamMember, actor: SignedIn, db: Db) -> CareTeamRow:
    try:
        return care_team.add_member(db, actor, patient_id, new)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.patch("/patients/{patient_id}/care-team/{member_id}")
def change_member(patient_id: uuid.UUID, member_id: uuid.UUID, change: CareTeamChange, actor: SignedIn, db: Db) -> CareTeamRow:
    try:
        return care_team.change_member(db, actor, patient_id, member_id, change)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.get("/providers/{provider_id}/patients")
def provider_patients(provider_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ProviderPatientRow]:
    try:
        return care_team.patients_of_provider(db, actor, provider_id)
    except tuple(_STATUS) as error:
        raise _refused(error) from None
