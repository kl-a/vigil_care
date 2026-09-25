from fastapi import FastAPI

from app.api import health
from app.core.config import Settings, refuse_unsafe_startup
from app.core.database import DatabaseCheck, postgres_check


def create_app(settings: Settings | None = None, database_check: DatabaseCheck | None = None) -> FastAPI:
    settings = settings or Settings()
    refuse_unsafe_startup(settings)

    app = FastAPI(title="Vigil", version="0.1.0")
    app.state.settings = settings
    app.state.database_check = database_check or postgres_check(settings.database_url)
    app.include_router(health.router)
    return app
