"""Care Team (#9): the Providers involved in each Patient's care, in a role, from when to when.

Patient data: staff read it ("view_patient_data") and change it ("verify_care_team"); developer admins never.
Every add, change or end is a Verification on the membership. At most one member is primary, and choosing
another moves it (signed off too).
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.changes import blank_to_none, changed_fields
from app.core.clock import practice_today
from app.core.permissions import require
from app.modules.patients.service import patient_names
from app.modules.practice.models import CareTeamMember, Provider
from app.modules.practice.providers import provider_names
from app.modules.practice.schemas import CareTeamChange, CareTeamRow, NewCareTeamMember, ProviderPatientRow

CARE_TEAM_SUBJECT = "care_team_member"


class PatientNotFound(LookupError):
    """No such live Patient in the actor's Practice."""


class MemberNotFound(LookupError):
    """No such Care Team membership for this Patient."""


class ProviderNotFound(LookupError):
    """No such Provider in the actor's Practice."""


class NoSuchProvider(ValueError):
    """The Provider to add isn't a live Provider in this Practice's directory."""


class EndsBeforeItStarts(ValueError):
    """A change would leave the membership ending before it starts."""


def _is_current(member: CareTeamMember) -> bool:
    return member.end_date is None or member.end_date >= practice_today()


def _row(member: CareTeamMember, provider_name: str) -> CareTeamRow:
    return CareTeamRow(
        id=member.id,
        provider_id=member.provider_id,
        provider_name=provider_name,
        role=member.role,
        is_primary=member.is_primary,
        start_date=member.start_date,
        end_date=member.end_date,
        notes=member.notes,
        is_current=_is_current(member),
    )


def _fields(member: CareTeamMember) -> dict[str, Any]:
    """The membership as a Verification records it (ids and dates as text)."""
    return {
        "provider_id": str(member.provider_id),
        "role": member.role,
        "is_primary": member.is_primary,
        "start_date": member.start_date.isoformat() if member.start_date else None,
        "end_date": member.end_date.isoformat() if member.end_date else None,
        "notes": member.notes,
    }


def _live_patient(db: Session, actor: Actor, patient_id: uuid.UUID) -> None:
    if not patient_names(db, actor.practice_id, {patient_id}):
        raise PatientNotFound()


def _members(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID) -> list[CareTeamMember]:
    return list(
        db.scalars(select(CareTeamMember).where(CareTeamMember.practice_id == practice_id, CareTeamMember.patient_id == patient_id))
    )


def _member(db: Session, actor: Actor, patient_id: uuid.UUID, member_id: uuid.UUID) -> CareTeamMember:
    member = db.scalars(
        select(CareTeamMember).where(
            CareTeamMember.id == member_id, CareTeamMember.patient_id == patient_id, CareTeamMember.practice_id == actor.practice_id
        )
    ).one_or_none()
    if member is None:
        raise MemberNotFound()
    return member


def _clear_primary(db: Session, actor: Actor, patient_id: uuid.UUID) -> None:
    """Before another member becomes primary (the database allows one at a time); the move is signed off too."""
    for member in _members(db, actor.practice_id, patient_id):
        if member.is_primary:
            audit.record_verification(
                db, actor, subject_table=CARE_TEAM_SUBJECT, subject_id=member.id, action="edit",
                before={"is_primary": True}, after={"is_primary": False},
            )
            member.is_primary = False
    db.flush()


def _rows(db: Session, actor: Actor, members: list[CareTeamMember]) -> list[CareTeamRow]:
    """Removed Providers keep their place in the history, by name."""
    names = provider_names(db, actor.practice_id, {m.provider_id for m in members}, include_removed=True)
    return [_row(member, names.get(member.provider_id, "Unknown Provider")) for member in members]


def _care_team_order(row: CareTeamRow) -> tuple[bool, bool, int, str, str]:
    """Current members first, the primary leading; then past ones, most recently ended first."""
    most_recent_end_first = -row.end_date.toordinal() if row.end_date else 0
    return (not row.is_current, not row.is_primary, most_recent_end_first, row.role, row.provider_name)


def care_team(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[CareTeamRow]:
    require(actor.job_title, "view_patient_data")
    _live_patient(db, actor, patient_id)
    rows = _rows(db, actor, _members(db, actor.practice_id, patient_id))
    return sorted(rows, key=_care_team_order)


def add_member(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewCareTeamMember) -> CareTeamRow:
    require(actor.job_title, "verify_care_team")
    _live_patient(db, actor, patient_id)
    if not provider_names(db, actor.practice_id, {new.provider_id}):
        raise NoSuchProvider("No such Provider in this Practice.")
    if new.is_primary:
        _clear_primary(db, actor, patient_id)
    member = CareTeamMember(practice_id=actor.practice_id, patient_id=patient_id, **blank_to_none(new.model_dump()))
    db.add(member)
    db.flush()
    audit.record_verification(db, actor, subject_table=CARE_TEAM_SUBJECT, subject_id=member.id, action="edit", after=_fields(member))
    [row] = _rows(db, actor, [member])
    return row


def change_member(db: Session, actor: Actor, patient_id: uuid.UUID, member_id: uuid.UUID, change: CareTeamChange) -> CareTeamRow:
    require(actor.job_title, "verify_care_team")
    _live_patient(db, actor, patient_id)
    member = _member(db, actor, patient_id, member_id)
    current = _fields(member)
    changed = changed_fields(current, change, required=("role",), mode="json")
    start = changed.get("start_date", current["start_date"])
    end = changed.get("end_date", current["end_date"])
    if start and end and end < start:
        raise EndsBeforeItStarts("A Care Team membership can't end before it starts.")
    if changed:
        audit.record_verification(
            db, actor, subject_table=CARE_TEAM_SUBJECT, subject_id=member.id, action="edit",
            before={field: current[field] for field in changed}, after=changed,
        )
        if changed.get("is_primary"):
            _clear_primary(db, actor, patient_id)
        for field, value in blank_to_none(change.model_dump(exclude_unset=True)).items():
            if field in changed:
                setattr(member, field, value)
        db.flush()
    [row] = _rows(db, actor, [member])
    return row


def patients_of_provider(db: Session, actor: Actor, provider_id: uuid.UUID) -> list[ProviderPatientRow]:
    """The live Patients a Provider is involved with: current memberships first."""
    require(actor.job_title, "view_patient_data")
    provider = db.scalars(select(Provider.id).where(Provider.id == provider_id, Provider.practice_id == actor.practice_id)).first()
    if provider is None:
        raise ProviderNotFound()
    members = list(
        db.scalars(select(CareTeamMember).where(CareTeamMember.practice_id == actor.practice_id, CareTeamMember.provider_id == provider_id))
    )
    names = patient_names(db, actor.practice_id, {m.patient_id for m in members})
    rows = [
        ProviderPatientRow(
            care_team_member_id=m.id,
            patient_id=m.patient_id,
            patient_name=names[m.patient_id],
            role=m.role,
            is_primary=m.is_primary,
            start_date=m.start_date,
            end_date=m.end_date,
            is_current=_is_current(m),
        )
        for m in members
        if m.patient_id in names
    ]
    return sorted(rows, key=lambda r: (not r.is_current, r.patient_name))
