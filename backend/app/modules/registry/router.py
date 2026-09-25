"""Specialty Modules in Settings (#15): list, switch (developer admins), and the active configuration."""

from fastapi import APIRouter, HTTPException, status

from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.registry import service
from app.modules.registry.schemas import ActiveConfiguration, ModuleChange, ModuleStatus

router = APIRouter(prefix="/modules", tags=["specialty modules"])


@router.get("")
def list_modules(actor: SignedIn, db: Db) -> list[ModuleStatus]:
    return service.list_modules(db, actor)


@router.get("/active")
def active_configuration(actor: SignedIn, db: Db) -> ActiveConfiguration:
    return service.active_configuration(db, actor)


@router.patch("/{key}")
def set_module_active(key: str, change: ModuleChange, actor: SignedIn, db: Db) -> ModuleStatus:
    try:
        return service.set_module_active(db, actor, key, change)
    except service.NotAllowed as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from None
    except service.ModuleNotInstalled as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from None
