from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api import health
from app.core.config import Settings, refuse_unsafe_startup
from app.core.database import DatabaseCheck, postgres_check, session_factory
from app.modules.accounts import router as accounts

SESSION_HOURS = 12


def create_app(settings: Settings | None = None, database_check: DatabaseCheck | None = None) -> FastAPI:
    settings = settings or Settings()
    refuse_unsafe_startup(settings)

    app = FastAPI(title="Vigil", version="0.1.0")
    app.state.settings = settings
    app.state.database_check = database_check or postgres_check(settings.database_url)
    app.state.sessionmaker = session_factory(settings.database_url)
    # Signed cookie holding only the User id. Stage 12 adds the inactivity lock and HTTPS-only cookies.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="vigil_session",
        max_age=SESSION_HOURS * 3600,
        same_site="lax",
    )
    app.include_router(health.router)
    app.include_router(accounts.router)
    if settings.environment == "dev" and settings.dev_login_enabled:
        app.include_router(accounts.dev_router)
    return app
