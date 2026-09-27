"""ECOG and CNS status (#44, design doc §6.3, §15 Stage 4c): Oncology values about the Patient over time,
entered by clinicians and trial coordinators. The latest ECOG is the current one. Built on `clinical.entry`.
"""

import uuid
from typing import Any, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.modules.clinical import entry
from app.specialties.oncology import access
from app.specialties.oncology.models import CnsStatus, PerformanceStatus
from app.specialties.oncology.schemas import (
    CnsStatusChange, CnsStatusRow, NewCnsStatus, NewPerformanceStatus, PerformanceScale, PerformanceStatusRow,
)

PERFORMANCE = "performance_status"
CNS = "cns_status"
CNS_FIELDS = (
    "assessed_on", "present", "lesion_count", "locations", "treated", "treatment_type", "symptomatic", "on_steroids",
    "steroid_dose_mg", "leptomeningeal",
)
M = TypeVar("M", PerformanceStatus, CnsStatus)


def _newest_first(db: Session, actor: Actor, model: type[M], patient_id: uuid.UUID) -> list[M]:
    return list(db.scalars(
        select(model)
        .where(model.practice_id == actor.practice_id, model.patient_id == patient_id)
        .order_by(model.assessed_on.desc(), model.created_at.desc())
    ))


# --- Performance status ---------------------------------------------------------------------------------------


def _performance_fields(row: PerformanceStatus) -> dict[str, Any]:
    return {"scale": row.scale, "value": row.value, "assessed_on": entry.audit_value(row.assessed_on)}


def _performance_rows(db: Session, actor: Actor, rows: list[PerformanceStatus]) -> list[PerformanceStatusRow]:
    entered = entry.entered(db, actor.practice_id, PERFORMANCE, (r.id for r in rows))
    return [
        PerformanceStatusRow(id=r.id, scale=cast(PerformanceScale, r.scale), value=r.value, assessed_on=r.assessed_on, entered=entered.get(r.id))
        for r in rows
    ]


def performance_statuses(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[PerformanceStatusRow]:
    """Newest first: the first is the current one."""
    access.require_view(db, actor, patient_id)
    return _performance_rows(db, actor, _newest_first(db, actor, PerformanceStatus, patient_id))


def add_performance_status(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewPerformanceStatus) -> PerformanceStatusRow:
    access.require_entry(db, actor, patient_id, PERFORMANCE)
    row = PerformanceStatus(patient_id=patient_id, **entry.entered_by(actor), **new.model_dump())
    db.add(row)
    entry.record_added(db, actor, PERFORMANCE, row, _performance_fields(row))
    [out] = _performance_rows(db, actor, [row])
    return out


def remove_performance_status(db: Session, actor: Actor, patient_id: uuid.UUID, row_id: uuid.UUID, reason: str) -> None:
    access.require_entry(db, actor, patient_id, PERFORMANCE)
    row = entry.live_row(db, actor, PerformanceStatus, patient_id, row_id)
    audit.soft_delete(db, actor, row, subject_table=PERFORMANCE, reason=reason, before=_performance_fields(row))


# --- CNS status -----------------------------------------------------------------------------------------------


def _cns_fields(row: CnsStatus) -> dict[str, Any]:
    return {field: entry.audit_value(getattr(row, field)) for field in CNS_FIELDS}


def _cns_rows(db: Session, actor: Actor, rows: list[CnsStatus]) -> list[CnsStatusRow]:
    entered = entry.entered(db, actor.practice_id, CNS, (r.id for r in rows))
    return [
        CnsStatusRow(id=r.id, entered=entered.get(r.id), **{field: getattr(r, field) for field in CNS_FIELDS})
        for r in rows
    ]


def cns_statuses(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[CnsStatusRow]:
    """Newest first."""
    access.require_view(db, actor, patient_id)
    return _cns_rows(db, actor, _newest_first(db, actor, CnsStatus, patient_id))


def add_cns_status(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewCnsStatus) -> CnsStatusRow:
    access.require_entry(db, actor, patient_id, CNS)
    row = CnsStatus(patient_id=patient_id, **entry.entered_by(actor), **new.model_dump())
    db.add(row)
    entry.record_added(db, actor, CNS, row, _cns_fields(row))
    [out] = _cns_rows(db, actor, [row])
    return out


def correct_cns_status(db: Session, actor: Actor, patient_id: uuid.UUID, row_id: uuid.UUID, change: CnsStatusChange) -> CnsStatusRow:
    access.require_entry(db, actor, patient_id, CNS)
    row = entry.live_row(db, actor, CnsStatus, patient_id, row_id)
    entry.correct(db, actor, CNS, row, _cns_fields(row), change, change.reason, required=("assessed_on",))
    [out] = _cns_rows(db, actor, [row])
    return out


def remove_cns_status(db: Session, actor: Actor, patient_id: uuid.UUID, row_id: uuid.UUID, reason: str) -> None:
    access.require_entry(db, actor, patient_id, CNS)
    row = entry.live_row(db, actor, CnsStatus, patient_id, row_id)
    audit.soft_delete(db, actor, row, subject_table=CNS, reason=reason, before=_cns_fields(row))


# --- In plain words, for the read-only view -----------------------------------------------------------------


def latest_lines(db: Session, practice_id: uuid.UUID, patient_id: uuid.UUID, when: Any) -> list[str]:
    """The latest ECOG (or KPS) and CNS status, e.g. "ECOG 2 (20 Sep 2026)", "CNS disease present: 1 lesion (…)"."""
    lines = []
    performance = db.scalars(
        select(PerformanceStatus).where(PerformanceStatus.practice_id == practice_id, PerformanceStatus.patient_id == patient_id)
        .order_by(PerformanceStatus.assessed_on.desc(), PerformanceStatus.created_at.desc()).limit(1)
    ).first()
    if performance:
        lines.append(f"{performance.scale} {performance.value} ({when(performance.assessed_on)})")
    cns = db.scalars(
        select(CnsStatus).where(CnsStatus.practice_id == practice_id, CnsStatus.patient_id == patient_id)
        .order_by(CnsStatus.assessed_on.desc(), CnsStatus.created_at.desc()).limit(1)
    ).first()
    if cns:
        if cns.present is False:
            lines.append(f"No CNS disease ({when(cns.assessed_on)})")
        elif cns.present:
            count = f": {cns.lesion_count} lesion{'s' if cns.lesion_count != 1 else ''}" if cns.lesion_count is not None else ""
            lines.append(f"CNS disease present{count} ({when(cns.assessed_on)})")
    return lines
