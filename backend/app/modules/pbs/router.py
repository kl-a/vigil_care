"""PBS Drug Lookup (#20, #30, design doc §5 screen 14). Refusals (403) come from the service. A PBS Refresh is
started like any other: POST /refreshes {"kind": "refresh_pbs"} (developer admins)."""

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.pbs import service
from app.modules.pbs.schemas import PbsDrug, PbsDrugPage, PbsFilters, PbsScheduleStatus

router = APIRouter(prefix="/pbs", tags=["pbs"])


@router.get("/schedule")
def schedule_status(actor: SignedIn, db: Db) -> PbsScheduleStatus:
    return service.schedule_status(db, actor)


@router.get("/filters")
def filters(actor: SignedIn, db: Db) -> PbsFilters:
    return service.filters(db, actor)


@router.get("/drugs")
def drugs(
    actor: SignedIn,
    db: Db,
    q: str = "",
    group: str | None = None,
    program: str | None = None,
    level: str | None = None,
    page: int = 1,
    page_size: int = service.PAGE_SIZE,
) -> PbsDrugPage:
    """Every drug in the current PBS Schedule, A–Z, narrowed by the filters (none: all of them)."""
    try:
        return service.drugs(db, actor, service.DrugFilters(q=q, group=group, program=program, level=level), page, page_size)
    except service.UnknownFilter as unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"No such filter: {unknown}") from None


@router.get("/drugs/{item_code}")
def drug(item_code: str, actor: SignedIn, db: Db) -> PbsDrug:
    try:
        return service.drug(db, actor, item_code)
    except service.DrugNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such item in the current PBS Schedule.") from None
