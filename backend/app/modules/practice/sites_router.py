"""Sites (#25, design doc §5 screen 19 Settings). Refusals (403) come from the service."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.audit.schemas import Removal
from app.modules.accounts.dependencies import Db, SignedIn
from app.modules.practice import sites
from app.modules.practice.schemas import NewSite, SiteChange, SiteRow

router = APIRouter(prefix="/sites", tags=["sites"])

_STATUS: dict[type[Exception], int] = {
    sites.SiteNotFound: status.HTTP_404_NOT_FOUND,
    sites.PrimarySiteNeeded: status.HTTP_409_CONFLICT,
}


def _refused(error: Exception) -> HTTPException:
    return HTTPException(_STATUS[type(error)], str(error) or "No such Site.")


@router.get("")
def list_sites(actor: SignedIn, db: Db) -> list[SiteRow]:
    return sites.list_sites(db, actor)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_site(new: NewSite, actor: SignedIn, db: Db) -> SiteRow:
    return sites.add_site(db, actor, new)


@router.patch("/{site_id}")
def change_site(site_id: uuid.UUID, change: SiteChange, actor: SignedIn, db: Db) -> SiteRow:
    try:
        return sites.change_site(db, actor, site_id, change)
    except tuple(_STATUS) as error:
        raise _refused(error) from None


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: uuid.UUID, removal: Removal, actor: SignedIn, db: Db) -> Response:
    try:
        sites.delete_site(db, actor, site_id, removal.reason)
    except tuple(_STATUS) as error:
        raise _refused(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
