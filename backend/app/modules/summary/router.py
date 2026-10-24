"""The Patient Summary (#47) and Open Items (#48). Refusals (403) come from the services."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.clinical import entry
from app.modules.summary import open_items, patient_summary
from app.modules.summary.schemas import OpenItem, PatientSummary, Who

router = APIRouter(tags=["summary"])


@router.get("/patients/{patient_id}/open-items")
def patient_open_items(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> list[OpenItem]:
    """Soonest first."""
    try:
        return open_items.patient_open_items(db, actor, patient_id)
    except entry.PatientNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such Patient.") from None


@router.get("/open-items")
def practice_open_items(actor: SignedIn, db: Db, type: str | None = None, who: Who | None = None) -> list[OpenItem]:
    """The Practice's queue for the Dashboard, filtered by type and by who can act."""
    return open_items.practice_open_items(db, actor, type, who)


@router.get("/patients/{patient_id}/summary")
def summary(patient_id: uuid.UUID, actor: SignedIn, db: Db) -> PatientSummary:
    """The Core's sections of the Patient Summary, each with when it was last updated."""
    try:
        return patient_summary.patient_summary(db, actor, patient_id)
    except entry.PatientNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such Patient.") from None
