import datetime as dt
import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.modules.clinical.schemas import (
    ClinicalNoteRow, ConditionRow, ImagingStudyRow, LabResultRow, LastUpdated, ManagementPlanRow, NextStepRow, TreatmentCourseRow,
)
from app.modules.medications.schemas import MedicationRow

# Who may act on an Open Item: any clinical staff (clinician, trial coordinator, secretary) or clinicians only.
Who = Literal["staff", "clinician"]


class Choice(BaseModel):
    id: uuid.UUID
    name: str


class OpenItemAction(BaseModel):
    """What clears an Open Item: a POST to the API, made as the User acting. `input` says what the User adds:
    nothing, an optional `note`, a required `reason`, or one of `choices` sent as `field`."""

    label: str
    path: str
    input: Literal["none", "note", "reason", "choose"] = "none"
    field: str | None = None
    choices: list[Choice] = []


class OpenItem(BaseModel):
    """Something someone must act on for a Patient. Derived each time; clears only when acted on."""

    type: str
    type_label: str
    patient_id: uuid.UUID
    # Filled in by the Core for the practice-wide queue.
    patient_name: str = ""
    title: str
    detail: str | None = None
    # The date it's about: a Next Step's due date, a result's collection date, a scan's date.
    dated: dt.date | None = None
    who: Who
    # Its icon, from a fixed set the screens draw: calendar, compare, help, scan, alert.
    icon: Literal["calendar", "compare", "help", "scan", "alert"]
    subject_table: str
    subject_id: uuid.UUID
    actions: list[OpenItemAction]
    # The Patient tab where it can be seen in full, and acted on in other ways.
    open_tab: str = "clinical-data"


# --- The Patient Summary (#47) -----------------------------------------------------------------------------


class TrendPoint(BaseModel):
    collected_at: dt.datetime
    value: Decimal


class ResultsSection(BaseModel):
    """Most Recent Results: each analyte's latest value (flagged), its trend, and the latest scans, each with when
    it was last updated."""

    latest_labs: list[LabResultRow]
    lab_trends: dict[str, list[TrendPoint]]
    updated: LastUpdated | None
    scans: list[ImagingStudyRow]
    scans_updated: LastUpdated | None


class TreatmentSection(BaseModel):
    """Recent Treatment: courses ongoing, or started or ended in the last 6 months."""

    courses: list[TreatmentCourseRow]
    updated: LastUpdated | None


class NotesSection(BaseModel):
    latest_note: ClinicalNoteRow | None
    latest_letter: ClinicalNoteRow | None
    updated: LastUpdated | None


class ManagementSection(BaseModel):
    """The current Management Plan, verbatim, and the Next Steps not yet done."""

    plan: ManagementPlanRow | None
    next_steps: list[NextStepRow]
    updated: LastUpdated | None


class HistorySection(BaseModel):
    """Medical History: Comorbidities (Conditions no Specialty Module extends) and current Medications."""

    comorbidities: list[ConditionRow]
    medications: list[MedicationRow]
    updated: LastUpdated | None


class PatientSummary(BaseModel):
    """The Core's sections of the Patient Summary. Registration comes from the Patient; Diagnosis from the
    Specialty Modules' own sections."""

    results: ResultsSection
    treatment: TreatmentSection
    notes: NotesSection
    management: ManagementSection
    history: HistorySection
    open_items: list[OpenItem]
