"""The Clinical Record entered by hand (#35, design doc §5 screen 9). Refusals (403) come from the services."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.clinical import conditions, entry
from app.modules.clinical.schemas import ConditionChange, ConditionRow, ModuleFacts, NewCondition

router = APIRouter(tags=["clinical record"])


_MISSING: dict[type[LookupError], str] = {
    entry.PatientNotFound: "No such Patient.",
    entry.RecordNotFound: "Not found for this Patient.",
}


def _missing(error: LookupError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, _MISSING[type(error)])


@router.get("/clinical/entry-rights")
def entry_rights(actor: SignedIn, db: Db) -> dict[str, bool]:
    """Which kinds of Clinical Record value the signed-in User may enter by hand."""
    return entry.entry_rights(db, actor)


@router.get("/patients/{patient_id}/inactive-module-facts")
def inactive_module_facts(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ModuleFacts]:
    try:
        return entry.inactive_module_facts(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.get("/patients/{patient_id}/conditions")
def list_conditions(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[ConditionRow]:
    try:
        return conditions.conditions(db, actor, patient_id)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.post("/patients/{patient_id}/conditions", status_code=status.HTTP_201_CREATED)
def add_condition(patient_id: uuid.UUID, new: NewCondition, actor: SignedIn, db: Db) -> ConditionRow:
    try:
        return conditions.add_condition(db, actor, patient_id, new)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.patch("/patients/{patient_id}/conditions/{condition_id}")
def change_condition(patient_id: uuid.UUID, condition_id: uuid.UUID, change: ConditionChange, actor: SignedIn, db: Db) -> ConditionRow:
    try:
        return conditions.change_condition(db, actor, patient_id, condition_id, change)
    except tuple(_MISSING) as error:
        raise _missing(error) from None


@router.delete("/patients/{patient_id}/conditions/{condition_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_condition(patient_id: uuid.UUID, condition_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        conditions.remove_condition(db, actor, patient_id, condition_id, removal.reason)
    except tuple(_MISSING) as error:
        raise _missing(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
