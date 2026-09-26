from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api import health
from app.core.config import Settings, keystore, refuse_unsafe_startup
from app.core.crypto import FieldCipher, TamperedCiphertext
from app.core.database import DatabaseCheck, postgres_check, session_factory
from app.core.permissions import NotAllowed
from app.modules.accounts import router as accounts
from app.modules.accounts import users_router
from app.modules.patients import router as patients
from app.modules.pbs import router as pbs
from app.modules.practice import router as practice
from app.modules.practice import care_team_router, providers_router, sites_router
from app.modules.registry import router as specialty_modules
from app.orchestrator import router as jobs
from app.orchestrator.queue import DbJobQueue

SESSION_HOURS = 12


def create_app(settings: Settings | None = None, database_check: DatabaseCheck | None = None) -> FastAPI:
    settings = settings or Settings()
    refuse_unsafe_startup(settings)

    # Interactive API docs are a developer tool: dev only, like the dev login.
    docs = settings.environment == "dev"
    app = FastAPI(
        title="Vigil",
        version="0.1.0",
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.settings = settings
    app.state.database_check = database_check or postgres_check(settings.database_url)
    app.state.sessionmaker = session_factory(settings.database_url)
    app.state.field_cipher = FieldCipher(keystore(settings))
    app.state.job_queue = DbJobQueue(app.state.sessionmaker)
    # Signed cookie holding only the User id and the Practice they act in.
    # Stage 13 adds the inactivity lock and HTTPS-only cookies.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="vigil_session",
        max_age=SESSION_HOURS * 3600,
        same_site="lax",
    )
    app.add_exception_handler(NotAllowed, _not_allowed)
    app.add_exception_handler(TamperedCiphertext, _undecryptable)
    app.include_router(health.router)
    app.include_router(accounts.router)
    app.include_router(users_router.router)
    app.include_router(practice.router)
    app.include_router(sites_router.router)
    app.include_router(providers_router.router)
    app.include_router(patients.router)
    app.include_router(care_team_router.router)
    app.include_router(pbs.router)
    app.include_router(jobs.router)
    app.include_router(specialty_modules.router)
    if settings.environment == "dev" and settings.dev_login_enabled:
        app.include_router(accounts.dev_router)
    return app


async def _not_allowed(request: Request, error: Exception) -> JSONResponse:
    """A service refused for the actor's Job Title (design doc §6.4)."""
    return JSONResponse({"detail": str(error)}, status_code=status.HTTP_403_FORBIDDEN)


async def _undecryptable(request: Request, error: Exception) -> JSONResponse:
    """Encrypted data that won't open: usually a database filled under a different VIGIL_ENCRYPTION_KEY."""
    return JSONResponse(
        {"detail": "Some Patient details can't be decrypted with the configured encryption key."},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
