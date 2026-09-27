"""Bloods and other labs (#42, design doc §6.3, §15 Stage 4c), entered by hand.

A panel is **one save with one Verification** (subject `lab_panel`, the results' `panel_id`); a single value is
corrected (reason) or removed on its own. Each value's H/L flag comes from the reference range entered with it:
the report's own range, deterministic, never a range Vigil supplies.
"""

import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.clock import PRACTICE_TIME_ZONE
from app.modules.clinical import entry
from app.modules.clinical.models import LabResult
from app.modules.clinical.schemas import Entered, LabFlag, LabPanelRow, LabResultChange, LabResultRow, NewLabPanel

FACT_KIND = "lab_result"
SUBJECT = "lab_result"
PANEL_SUBJECT = "lab_panel"


def flag_for(value: Decimal | None, low: Decimal | None, high: Decimal | None) -> LabFlag | None:
    """"low", "high" or "normal" against the range entered; None without a number or a range."""
    if value is None or (low is None and high is None):
        return None
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    return "normal"


def _fields(result: LabResult) -> dict[str, Any]:
    """A result as its Verifications record it (numbers as text, so 98 stays "98")."""
    return {
        "analyte": result.analyte, "value": entry.audit_value(result.value), "value_text": result.value_text, "unit": result.unit,
        "ref_low": entry.audit_value(result.ref_low), "ref_high": entry.audit_value(result.ref_high),
    }


def _entered(db: Session, actor: Actor, results: list[LabResult]) -> dict[uuid.UUID, Entered]:
    """Who entered each result: the Verification of the panel it came in."""
    panels = entry.entered(db, actor.practice_id, PANEL_SUBJECT, {r.panel_id for r in results if r.panel_id})
    return {r.id: panels[r.panel_id] for r in results if r.panel_id in panels}


def _rows(db: Session, actor: Actor, results: list[LabResult]) -> list[LabResultRow]:
    entered = _entered(db, actor, results)
    return [
        LabResultRow(
            id=r.id, panel_id=r.panel_id, panel=r.panel, analyte=r.analyte, value=r.value, value_text=r.value_text,
            unit=r.unit, ref_low=r.ref_low, ref_high=r.ref_high, flag=cast(LabFlag | None, r.flag),
            collected_at=r.collected_at.astimezone(PRACTICE_TIME_ZONE), entered=entered.get(r.id),
        )
        for r in results
    ]


def lab_results(db: Session, actor: Actor, patient_id: uuid.UUID) -> list[LabResultRow]:
    """Newest first, then by analyte within a collection (trends read each analyte over time)."""
    entry.require_view(db, actor, patient_id)
    results = db.scalars(
        select(LabResult)
        .where(LabResult.practice_id == actor.practice_id, LabResult.patient_id == patient_id)
        .order_by(LabResult.collected_at.desc(), LabResult.created_at, LabResult.id)
    )
    return _rows(db, actor, list(results))


def add_panel(db: Session, actor: Actor, patient_id: uuid.UUID, new: NewLabPanel) -> LabPanelRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    panel_id = uuid.uuid4()
    collected_at = datetime.combine(new.collected_on, new.collected_time or time(0), tzinfo=PRACTICE_TIME_ZONE)
    results = [
        LabResult(
            patient_id=patient_id, **entry.entered_by(actor), panel_id=panel_id, panel=new.panel, collected_at=collected_at,
            flag=flag_for(value.value, value.ref_low, value.ref_high), **value.model_dump(),
        )
        for value in new.results
    ]
    db.add_all(results)
    db.flush()
    audit.record_verification(
        db, actor, subject_table=PANEL_SUBJECT, subject_id=panel_id, action="edit",
        after={"panel": new.panel, "collected_at": collected_at.isoformat(), "results": [_fields(r) for r in results]},
    )
    rows = _rows(db, actor, results)
    return LabPanelRow(panel_id=panel_id, panel=new.panel, collected_at=rows[0].collected_at, results=rows)


def change_result(db: Session, actor: Actor, patient_id: uuid.UUID, result_id: uuid.UUID, change: LabResultChange) -> LabResultRow:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    result = entry.live_row(db, actor, LabResult, patient_id, result_id)
    entry.correct(db, actor, SUBJECT, result, _fields(result), change, change.reason, required=("analyte",))
    result.flag = flag_for(result.value, result.ref_low, result.ref_high)
    db.flush()
    [row] = _rows(db, actor, [result])
    return row


def remove_result(db: Session, actor: Actor, patient_id: uuid.UUID, result_id: uuid.UUID, reason: str) -> None:
    entry.require_entry(db, actor, patient_id, FACT_KIND)
    result = entry.live_row(db, actor, LabResult, patient_id, result_id)
    audit.soft_delete(db, actor, result, subject_table=SUBJECT, reason=reason, before=_fields(result))
