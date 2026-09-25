from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app.core.config import Environment, Settings
from app.core.database import DatabaseCheck

# A Support View: IDs and states only (design doc §6.4).
router = APIRouter(tags=["support"])


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    environment: Environment
    database: Literal["ok", "unreachable"]
    vlm_worker: Literal["not_configured", "configured"]


@router.get("/health", response_model=Health)
def health(request: Request, response: Response) -> Health:
    settings: Settings = request.app.state.settings
    database_check: DatabaseCheck = request.app.state.database_check
    database_ok = database_check()
    if not database_ok:
        response.status_code = 503
    return Health(
        status="ok" if database_ok else "degraded",
        environment=settings.environment,
        database="ok" if database_ok else "unreachable",
        vlm_worker="configured" if settings.vlm_worker_url else "not_configured",
    )
