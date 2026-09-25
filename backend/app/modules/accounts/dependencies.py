"""The accounts module's public FastAPI dependencies. Every other module's routes use `SignedIn`."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import db_session
from app.core.permissions import Permission, may
from app.modules.accounts import service
from app.modules.accounts.schemas import CurrentUser

SESSION_USER = "user_id"

Db = Annotated[Session, Depends(db_session)]


def current_user(request: Request, db: Db) -> CurrentUser:
    """401 unless the session names an active User."""
    user_id = request.session.get(SESSION_USER)
    user = service.signed_in_user(db, uuid.UUID(user_id)) if user_id else None
    if user is None:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in.")
    return user


SignedIn = Annotated[CurrentUser, Depends(current_user)]


def requires(permission: Permission) -> Callable[[CurrentUser], CurrentUser]:
    """A dependency: 403 unless the signed-in User's Job Title has this permission (design doc §6.4)."""

    def check(user: SignedIn) -> CurrentUser:
        if not may(user.job_title, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not available for your Job Title.")
        return user

    return check
