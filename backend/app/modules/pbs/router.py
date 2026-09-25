"""PBS Drug Lookup (#20, design doc §5 screen 14). Refusals (403) come from the service. A PBS Refresh is
started like any other: POST /refreshes {"kind": "refresh_pbs"} (developer admins)."""

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.pbs import service
from app.modules.pbs.schemas import PbsDrug, PbsDrugRow, PbsScheduleStatus

router = APIRouter(prefix="/pbs", tags=["pbs"])


@router.get("/schedule")
def schedule_status(actor: SignedIn, db: Db) -> PbsScheduleStatus:
    return service.schedule_status(db, actor)


@router.get("/drugs")
def search(actor: SignedIn, db: Db, q: str = "") -> list[PbsDrugRow]:
    return service.search(db, actor, q)


@router.get("/drugs/{item_code}")
def drug(item_code: str, actor: SignedIn, db: Db) -> PbsDrug:
    try:
        return service.drug(db, actor, item_code)
    except service.DrugNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such item in the current PBS Schedule.") from None
