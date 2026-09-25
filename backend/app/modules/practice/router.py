"""Practice details (#14, design doc §5 screen 19)."""

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.practice import service
from app.modules.practice.schemas import PracticeChange, PracticeDetails

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("")
def practice_details(actor: SignedIn, db: Db) -> PracticeDetails:
    return service.practice_details(db, actor)


@router.patch("")
def change_practice(change: PracticeChange, actor: SignedIn, db: Db) -> PracticeDetails:
    try:
        return service.change_practice(db, actor, change)
    except service.NotAllowed as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from None
