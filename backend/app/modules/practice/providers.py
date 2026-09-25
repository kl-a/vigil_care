"""Provider directory (#7): the Practice's clinicians, referrers, specialists and trial-site contacts.

Anyone signed in reads it (User Management links a User to their own Provider); "manage_providers" edits it.
Used for Care Teams, letters and referrals.
"""

import uuid
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.changes import blank_to_none, changed_fields
from app.core.permissions import require
from app.modules.practice.models import Provider, ProviderSpecialty
from app.modules.practice.schemas import NewProvider, ProviderChange, ProviderRow

PROVIDER_SUBJECT = "provider"
# Sent empty in an edit, these are ignored rather than cleared.
REQUIRED = ("first_name", "last_name", "specialty", "is_internal")


class ProviderNotFound(LookupError):
    """No such Provider in the actor's Practice."""


class ProviderNumberTaken(ValueError):
    """Provider numbers are unique within the Practice, including removed Providers'."""


def display_name(provider: Provider) -> str:
    return " ".join(part for part in (provider.title, provider.first_name, provider.last_name) if part)


def _row(provider: Provider) -> ProviderRow:
    return ProviderRow(
        id=provider.id,
        display_name=display_name(provider),
        title=provider.title,
        first_name=provider.first_name,
        last_name=provider.last_name,
        provider_number=provider.provider_number,
        specialty=provider.specialty,
        is_internal=provider.is_internal,
        organisation=provider.organisation,
        phone=provider.phone,
        email=provider.email,
        fax=provider.fax,
        notes=provider.notes,
    )


def _fields(provider: Provider) -> dict[str, Any]:
    return _row(provider).model_dump(exclude={"id", "display_name"})


def _in_practice(practice_id: uuid.UUID) -> Select[Provider]:
    return select(Provider).where(Provider.practice_id == practice_id)


def _provider(db: Session, actor: Actor, provider_id: uuid.UUID) -> Provider:
    provider = db.scalars(_in_practice(actor.practice_id).where(Provider.id == provider_id)).one_or_none()
    if provider is None:
        raise ProviderNotFound()
    return provider


def _check_number_free(db: Session, actor: Actor, number: str | None, provider_id: uuid.UUID | None = None) -> None:
    """Numbers stay taken after a soft delete, so they're checked including removed Providers."""
    if not number:
        return
    query = _in_practice(actor.practice_id).where(Provider.provider_number == number)
    if provider_id is not None:
        query = query.where(Provider.id != provider_id)
    holder = db.scalars(query.execution_options(include_deleted=True)).first()
    if holder is not None:
        who = "a removed Provider" if holder.deleted_at is not None else display_name(holder)
        raise ProviderNumberTaken(f"Provider number {number} is already used by {who}.")


def list_providers(
    db: Session, actor: Actor, q: str | None = None, specialty: ProviderSpecialty | None = None, internal: bool | None = None
) -> list[ProviderRow]:
    """Search matches every word of `q` against first or last name."""
    query = _in_practice(actor.practice_id)
    for word in (q or "").split():
        pattern = f"%{word}%"
        query = query.where(or_(Provider.first_name.ilike(pattern), Provider.last_name.ilike(pattern)))
    if specialty is not None:
        query = query.where(Provider.specialty == specialty)
    if internal is not None:
        query = query.where(Provider.is_internal == internal)
    return [_row(p) for p in db.scalars(query.order_by(Provider.last_name, Provider.first_name))]


def provider_detail(db: Session, actor: Actor, provider_id: uuid.UUID) -> ProviderRow:
    return _row(_provider(db, actor, provider_id))


def provider_names(
    db: Session, practice_id: uuid.UUID, provider_ids: set[uuid.UUID], include_removed: bool = False
) -> dict[uuid.UUID, str]:
    """Providers' names, for other modules (a User's linked Provider, Care Teams). Live ones only, unless a
    history needs removed Providers named too."""
    query = _in_practice(practice_id).where(Provider.id.in_(provider_ids))
    providers = db.scalars(query.execution_options(include_deleted=include_removed))
    return {provider.id: display_name(provider) for provider in providers}


def add_provider(db: Session, actor: Actor, new: NewProvider) -> ProviderRow:
    require(actor.job_title, "manage_providers")
    values = blank_to_none(new.model_dump())
    _check_number_free(db, actor, values["provider_number"])
    provider = Provider(practice_id=actor.practice_id, **values)
    db.add(provider)
    db.flush()
    audit.record_verification(
        db, actor, subject_table=PROVIDER_SUBJECT, subject_id=provider.id, action="edit", after=_fields(provider)
    )
    return _row(provider)


def change_provider(db: Session, actor: Actor, provider_id: uuid.UUID, change: ProviderChange) -> ProviderRow:
    require(actor.job_title, "manage_providers")
    provider = _provider(db, actor, provider_id)
    current = _fields(provider)
    changed = changed_fields(current, change, required=REQUIRED)
    if not changed:
        return _row(provider)
    if "provider_number" in changed:
        _check_number_free(db, actor, changed["provider_number"], provider.id)
    audit.record_verification(
        db, actor, subject_table=PROVIDER_SUBJECT, subject_id=provider.id, action="edit",
        before={field: current[field] for field in changed}, after=changed,
    )
    for field, value in changed.items():
        setattr(provider, field, value)
    db.flush()
    return _row(provider)


def delete_provider(db: Session, actor: Actor, provider_id: uuid.UUID, reason: str) -> None:
    """Care Teams and linked Users keep pointing at it; it just disappears from the directory."""
    require(actor.job_title, "manage_providers")
    provider = _provider(db, actor, provider_id)
    audit.soft_delete(db, actor, provider, subject_table=PROVIDER_SUBJECT, reason=reason, before=_fields(provider))
