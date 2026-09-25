"""User Management (#6, design doc §5 screen 18). The service refuses Job Titles without "manage_users" (§6.4)."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts import service
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.accounts.schemas import NewUser, UserChange, UserDetail, UserRow

router = APIRouter(prefix="/users", tags=["users"])

_STATUS: dict[type[Exception], int] = {
    service.UserNotFound: status.HTTP_404_NOT_FOUND,
    service.UsernameTaken: status.HTTP_409_CONFLICT,
    service.CantChangeYourself: status.HTTP_409_CONFLICT,
    service.DisplayNameNeeded: status.HTTP_422_UNPROCESSABLE_CONTENT,
}
_MESSAGE: dict[type[Exception], str] = {service.UserNotFound: "No such User."}


def _refused(error: Exception) -> HTTPException:
    kind = type(error)
    return HTTPException(_STATUS[kind], _MESSAGE.get(kind, str(error)))


@router.get("")
def list_users(actor: SignedIn, db: Db) -> list[UserRow]:
    try:
        return service.list_users(db, actor)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(new: NewUser, actor: SignedIn, db: Db) -> UserRow:
    try:
        return service.create_user(db, actor, new)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.get("/{user_id}")
def user_detail(user_id: uuid.UUID, actor: SignedIn, db: Db) -> UserDetail:
    try:
        return service.user_detail(db, actor, user_id)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.patch("/{user_id}")
def change_user(user_id: uuid.UUID, change: UserChange, actor: SignedIn, db: Db) -> UserRow:
    try:
        return service.change_user(db, actor, user_id, change)
    except tuple(_STATUS) as error:
        raise _refused(error) from None
