"""Provider directory (#7, design doc §5 screen 17). Refusals (403) come from the service."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.practice import providers
from app.modules.practice.models import ProviderSpecialty
from app.modules.practice.schemas import NewProvider, ProviderChange, ProviderRow

router = APIRouter(prefix="/providers", tags=["providers"])

_STATUS: dict[type[Exception], int] = {
    providers.ProviderNotFound: status.HTTP_404_NOT_FOUND,
    providers.ProviderNumberTaken: status.HTTP_409_CONFLICT,
}


def _refused(error: Exception) -> HTTPException:
    return HTTPException(_STATUS[type(error)], str(error) or "No such Provider.")


@router.get("")
def list_providers(
    actor: SignedIn, db: Db, q: str | None = None, specialty: ProviderSpecialty | None = None, internal: bool | None = None
) -> list[ProviderRow]:
    return providers.list_providers(db, actor, q=q, specialty=specialty, internal=internal)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_provider(new: NewProvider, actor: SignedIn, db: Db) -> ProviderRow:
    try:
        return providers.add_provider(db, actor, new)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.get("/{provider_id}")
def provider_detail(provider_id: uuid.UUID, actor: SignedIn, db: Db) -> ProviderRow:
    try:
        return providers.provider_detail(db, actor, provider_id)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.patch("/{provider_id}")
def change_provider(provider_id: uuid.UUID, change: ProviderChange, actor: SignedIn, db: Db) -> ProviderRow:
    try:
        return providers.change_provider(db, actor, provider_id, change)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        providers.delete_provider(db, actor, provider_id, removal.reason)
    except tuple(_STATUS) as error:
        raise _refused(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
