"""Sites (#25): where the Practice sees Patients. Anyone signed in reads them; "change_settings" manages them.

A Practice has exactly one primary Site once it has any: the first Site is primary, choosing another moves
it, and the primary can't be deleted.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.permissions import require
from app.modules.practice.models import Site
from app.modules.practice.schemas import NewSite, SiteChange, SiteRow

SITE_SUBJECT = "site"


class SiteNotFound(LookupError):
    """No such Site in the actor's Practice."""


class PrimarySiteNeeded(ValueError):
    pass


def _row(site: Site) -> SiteRow:
    return SiteRow(
        id=site.id,
        name=site.name,
        address=site.address,
        lat=float(site.lat) if site.lat is not None else None,
        lng=float(site.lng) if site.lng is not None else None,
        is_primary=site.is_primary,
    )


def _fields(site: Site) -> dict[str, Any]:
    return _row(site).model_dump(exclude={"id"})


def _site(db: Session, actor: Actor, site_id: uuid.UUID) -> Site:
    site = db.scalars(select(Site).where(Site.id == site_id, Site.practice_id == actor.practice_id)).one_or_none()
    if site is None:
        raise SiteNotFound()
    return site


def _clear_primary(db: Session, practice_id: uuid.UUID) -> None:
    """Before another Site becomes primary: the database allows only one at a time."""
    for site in db.scalars(select(Site).where(Site.practice_id == practice_id, Site.is_primary)):
        site.is_primary = False
    db.flush()


def _decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def list_sites(db: Session, actor: Actor) -> list[SiteRow]:
    """The primary Site first."""
    sites = db.scalars(
        select(Site).where(Site.practice_id == actor.practice_id).order_by(Site.is_primary.desc(), Site.name)
    )
    return [_row(site) for site in sites]


def add_site(db: Session, actor: Actor, new: NewSite) -> SiteRow:
    require(actor.job_title, "change_settings")
    is_primary = db.scalars(select(Site.id).where(Site.practice_id == actor.practice_id)).first() is None
    site = Site(
        practice_id=actor.practice_id,
        name=new.name,
        address=new.address or None,
        lat=_decimal(new.lat),
        lng=_decimal(new.lng),
        is_primary=is_primary,
    )
    db.add(site)
    db.flush()
    audit.record_verification(db, actor, subject_table=SITE_SUBJECT, subject_id=site.id, action="edit", after=_fields(site))
    return _row(site)


def change_site(db: Session, actor: Actor, site_id: uuid.UUID, change: SiteChange) -> SiteRow:
    require(actor.job_title, "change_settings")
    site = _site(db, actor, site_id)
    current = _fields(site)
    # Empty text clears an optional field.
    requested = {
        field: (value or None) if isinstance(value, str) else value
        for field, value in change.model_dump(exclude_unset=True).items()
    }
    changed = {field: value for field, value in requested.items() if value != current[field]}
    if not changed:
        return _row(site)
    audit.record_verification(
        db, actor, subject_table=SITE_SUBJECT, subject_id=site.id, action="edit",
        before={field: current[field] for field in changed}, after=changed,
    )
    if changed.get("is_primary"):
        _clear_primary(db, actor.practice_id)
    for field, value in changed.items():
        setattr(site, field, _decimal(value) if field in ("lat", "lng") else value)
    db.flush()
    return _row(site)


def delete_site(db: Session, actor: Actor, site_id: uuid.UUID, reason: str) -> None:
    require(actor.job_title, "change_settings")
    site = _site(db, actor, site_id)
    if site.is_primary:
        raise PrimarySiteNeeded("The primary Site can't be deleted. Choose another Site as primary first.")
    audit.soft_delete(db, actor, site, subject_table=SITE_SUBJECT, reason=reason, before=_fields(site))
