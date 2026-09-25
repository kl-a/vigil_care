"""Sign-in routes. The dev-login routes are registered only in dev with the dev login enabled."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.seams.identity import LoginRefused
from app.modules.accounts import service
from app.modules.accounts.dependencies import SESSION_USER, Db, SignedIn
from app.modules.accounts.schemas import CurrentUser, DevLoginChoice, DevLoginRequest

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
        user = service.dev_login(db, body.user_id)
    except LoginRefused:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That User can't sign in.") from None
    request.session.clear()
    request.session[SESSION_USER] = str(user.id)
    return user
