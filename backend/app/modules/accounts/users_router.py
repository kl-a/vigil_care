"""User Management (#6, design doc §5 screen 18). Open to Job Titles with "manage_users" (§6.4)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.accounts import service
from app.modules.accounts.dependencies import Db, requires
from app.modules.accounts.schemas import CurrentUser, NewUser, UserChange, UserDetail, UserRow

Manager = Annotated[CurrentUser, Depends(requires("manage_users"))]

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(actor: Manager, db: Db) -> list[UserRow]:
    return service.list_users(db, actor.practice_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(new: NewUser, actor: Manager, db: Db) -> UserRow:
    try:
        return service.create_user(db, actor, new)
    except service.UsernameTaken as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None


@router.get("/{user_id}")
def user_detail(user_id: uuid.UUID, actor: Manager, db: Db) -> UserDetail:
    try:
        return service.user_detail(db, actor.practice_id, user_id)
    except service.UserNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such User.") from None


@router.patch("/{user_id}")
def change_user(user_id: uuid.UUID, change: UserChange, actor: Manager, db: Db) -> UserRow:
    try:
        return service.change_user(db, actor, user_id, change)
    except service.UserNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such User.") from None
    except service.CantChangeYourself as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from None
