"""The Patient Summary (#47, design doc §5 screen 15): the consultation page's Core sections, built from the
Clinical Record each time (nothing stored). Each section says when it was last updated: the Verification of its
newest value. An empty section is sent empty, never left out; the screen says "None recorded".
"""

import uuid
from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.clock import practice_today
from app.modules.clinical import conditions, entry, imaging, labs, plan_and_notes, treatment_courses
from app.modules.medications import medications
from app.modules.summary import open_items
from app.modules.clinical.schemas import LabResultRow
from app.modules.summary.schemas import (
    HistorySection, ManagementSection, NotesSection, PatientSummary, ResultsSection, TreatmentSection, TrendPoint,
)

RECENT = timedelta(days=183)  # "the last 6 months"
LATEST_SCANS = 2


def patient_summary(db: Session, actor: Actor, patient_id: uuid.UUID) -> PatientSummary:
    entry.require_view(db, actor, patient_id)
    return PatientSummary(
        results=_results(db, actor, patient_id), treatment=_treatment(db, actor, patient_id), notes=_notes(db, actor, patient_id),
        management=_management(db, actor, patient_id), history=_history(db, actor, patient_id),
        open_items=open_items.derive(db, actor.practice_id, {patient_id}),
    )


def _results(db: Session, actor: Actor, patient_id: uuid.UUID) -> ResultsSection:
    results = labs.lab_results(db, actor, patient_id)  # newest first
    latest: dict[str, LabResultRow] = {}
    trends: dict[str, list[TrendPoint]] = defaultdict(list)
    for result in results:
        latest.setdefault(result.analyte, result)
        if result.value is not None:
            trends[result.analyte].insert(0, TrendPoint(collected_at=result.collected_at, value=result.value))
    scans = imaging.imaging_studies(db, actor, patient_id)[:LATEST_SCANS]
    updated = entry.last_updated(db, actor.practice_id, {
        labs.SUBJECT: (r.id for r in results), labs.PANEL_SUBJECT: (r.panel_id for r in results if r.panel_id),
    })
    scans_updated = entry.last_updated(db, actor.practice_id, {
        imaging.STUDY: (s.id for s in scans), imaging.FINDING: (f.id for s in scans for f in s.findings),
    })
    return ResultsSection(latest_labs=list(latest.values()), lab_trends=dict(trends), updated=updated, scans=scans, scans_updated=scans_updated)


def _treatment(db: Session, actor: Actor, patient_id: uuid.UUID) -> TreatmentSection:
    since = practice_today() - RECENT
    courses = [
        c for c in treatment_courses.treatment_courses(db, actor, patient_id)
        if c.ongoing or (c.start_date and c.start_date >= since) or (c.end_date and c.end_date >= since)
    ]
    return TreatmentSection(courses=courses, updated=entry.last_updated(db, actor.practice_id, {treatment_courses.SUBJECT: (c.id for c in courses)}))


def _notes(db: Session, actor: Actor, patient_id: uuid.UUID) -> NotesSection:
    notes = plan_and_notes.clinical_notes(db, actor, patient_id)  # newest first
    note = next((n for n in notes if n.note_type == "clinical_note"), None)
    letter = next((n for n in notes if n.note_type == "letter_to_referrer"), None)
    shown = [n.id for n in (note, letter) if n]
    return NotesSection(latest_note=note, latest_letter=letter, updated=entry.last_updated(db, actor.practice_id, {plan_and_notes.NOTE: shown}))


def _management(db: Session, actor: Actor, patient_id: uuid.UUID) -> ManagementSection:
    plans = plan_and_notes.management_plans(db, actor, patient_id)
    steps = [s for s in plan_and_notes.next_steps(db, actor, patient_id) if s.done is None]
    updated = entry.last_updated(db, actor.practice_id, {plan_and_notes.PLAN: [p.id for p in plans[:1]], plan_and_notes.NEXT_STEP: [s.id for s in steps]})
    return ManagementSection(plan=plans[0] if plans else None, next_steps=steps, updated=updated)


def _history(db: Session, actor: Actor, patient_id: uuid.UUID) -> HistorySection:
    comorbidities = [c for c in conditions.conditions(db, actor, patient_id) if c.extended_by_module is None]
    current = [m for m in medications.medications(db, actor, patient_id) if not medications.is_stopped(m.status)]
    updated = entry.last_updated(db, actor.practice_id, {
        conditions.SUBJECT: (c.id for c in comorbidities), medications.SUBJECT: (m.id for m in current),
    })
    return HistorySection(comorbidities=comorbidities, medications=current, updated=updated)
