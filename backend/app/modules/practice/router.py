"""Practice details (#14, design doc §5 screen 19). Refusals (403) come from the service."""

from fastapi import APIRouter

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.practice import service
from app.modules.practice.schemas import PracticeChange, PracticeDetails

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("")
def practice_details(actor: SignedIn, db: Db) -> PracticeDetails:
    return service.practice_details(db, actor)


@router.patch("")
def change_practice(change: PracticeChange, actor: SignedIn, db: Db) -> PracticeDetails:
    return service.change_practice(db, actor, change)
