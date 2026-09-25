"""Sign-in routes. The dev-login routes are registered only in dev with the dev login enabled."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import db_session
from app.core.seams.identity import DevLogin, DevLoginCredentials, LoginRefused
from app.modules.accounts import service
from app.modules.accounts.schemas import CurrentUser, DevLoginChoice, DevLoginRequest

SESSION_USER = "user_id"

Db = Annotated[Session, Depends(db_session)]


def current_user(request: Request, db: Db) -> CurrentUser:
    """Every non-public endpoint depends on this: 401 unless the session names an active User."""
    user_id = request.session.get(SESSION_USER)
    user = service.signed_in_user(db, uuid.UUID(user_id)) if user_id else None
    if user is None:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in.")
    return user


SignedIn = Annotated[CurrentUser, Depends(current_user)]

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(user: SignedIn) -> CurrentUser:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, user: SignedIn) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


dev_router = APIRouter(prefix="/auth/dev-login", tags=["auth (dev only)"])


@dev_router.get("/users")
def dev_login_users(db: Db) -> list[DevLoginChoice]:
    return service.dev_login_choices(db)


@dev_router.post("")
def dev_login(body: DevLoginRequest, request: Request, db: Db) -> CurrentUser:
    try:
        user_id = DevLogin(service.ActiveUsers(db)).authenticate(DevLoginCredentials(body.user_id))
    except LoginRefused:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That User can't sign in.") from None
    request.session.clear()
    request.session[SESSION_USER] = str(user_id)
    user = service.signed_in_user(db, user_id)
    assert user is not None
    return user
