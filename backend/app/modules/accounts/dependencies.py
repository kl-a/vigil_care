"""The accounts module's public FastAPI dependencies. Every other module's routes use `SignedIn`."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import db_session
from app.modules.accounts import service
from app.modules.accounts.schemas import CurrentUser

SESSION_USER = "user_id"
# The Practice the session acts in: one of the User's Practice Memberships.
SESSION_PRACTICE = "practice_id"

Db = Annotated[Session, Depends(db_session)]


def current_user(request: Request, db: Db) -> CurrentUser:
    """401 unless the session names a User with an active Membership in its Practice."""
    user_id, practice_id = request.session.get(SESSION_USER), request.session.get(SESSION_PRACTICE)
    user = service.signed_in_user(db, uuid.UUID(user_id), uuid.UUID(practice_id)) if user_id and practice_id else None
    if user is None:
        request.session.clear()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in.")
    return user


SignedIn = Annotated[CurrentUser, Depends(current_user)]

