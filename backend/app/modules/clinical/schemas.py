import datetime as dt
import uuid
from typing import Annotated, Literal

from decimal import Decimal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.audit.schemas import Reason
from app.core.vocabulary import JobTitle

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
ConditionStatus = Literal["active", "resolved"]


class Entered(BaseModel):
    """Who entered a value by hand, their Job Title then, and when (its first Verification)."""

    by: str
    job_title: JobTitle
    at: dt.datetime


class NewCondition(BaseModel):
    name: Name
    status: ConditionStatus = "active"
    onset_date: dt.date | None = None
    notes: Notes | None = None


class ConditionChange(BaseModel):
    """Only the fields that change, and why (once for the whole save)."""

    name: Name | None = None
    status: ConditionStatus | None = None
    onset_date: dt.date | None = None
    notes: Notes | None = None
    reason: Reason


class ConditionRow(BaseModel):
    id: uuid.UUID
    name: str
    status: ConditionStatus
    onset_date: dt.date | None
    notes: str | None
    # The Specialty Module that extends it (e.g. "oncology" for a primary cancer), active or not.
    extended_by_module: str | None
    entered: Entered | None


class ModuleFacts(BaseModel):
    """A Specialty Module inactive at this Practice, and its recorded facts for the Patient in plain words."""

    module: str
    display_name: str
    facts: list[str]


# Quoted verbatim: kept exactly as entered (no trimming), never rewritten.
Verbatim = Annotated[str, StringConstraints(min_length=1, max_length=20000)]
NoteType = Literal["clinical_note", "letter_to_referrer", "discharge_summary"]
NoteContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
Unit = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]
NextStepKind = Literal["rescan", "mdt", "trial_window", "review", "other"]


class NewManagementPlan(BaseModel):
    plan_text: Verbatim
    plan_date: dt.date | None = None
    authored_by_provider_id: uuid.UUID | None = None


class ManagementPlanChange(BaseModel):
    plan_text: Verbatim | None = None
    plan_date: dt.date | None = None
    authored_by_provider_id: uuid.UUID | None = None
    reason: Reason


class ManagementPlanRow(BaseModel):
    """The treating clinician's plan, exactly as written, with who wrote it (a Provider) and who entered it."""

    id: uuid.UUID
    plan_text: str
    plan_date: dt.date | None
    authored_by_provider_id: uuid.UUID | None
    author_name: str | None
    entered: Entered | None


class NewClinicalNote(BaseModel):
    note_type: NoteType
    note_date: dt.date | None = None
    author_provider_id: uuid.UUID | None = None
    recipient_provider_id: uuid.UUID | None = None
    content: NoteContent


class ClinicalNoteChange(BaseModel):
    note_type: NoteType | None = None
    note_date: dt.date | None = None
    author_provider_id: uuid.UUID | None = None
    recipient_provider_id: uuid.UUID | None = None
    content: NoteContent | None = None
    reason: Reason


class ClinicalNoteRow(BaseModel):
    id: uuid.UUID
    note_type: NoteType
    note_date: dt.date | None
    author_provider_id: uuid.UUID | None
    author_name: str | None
    recipient_provider_id: uuid.UUID | None
    recipient_name: str | None
    content: str | None
    entered: Entered | None


class NewNextStep(BaseModel):
    kind: NextStepKind
    description: Name
    due_date: dt.date | None = None


class NextStepChange(BaseModel):
    kind: NextStepKind | None = None
    description: Name | None = None
    due_date: dt.date | None = None
    reason: Reason


class Done(BaseModel):
    """Who marked a Next Step done, and when."""

    by: str
    at: dt.datetime


class NextStepRow(BaseModel):
    """A dated item alongside the Management Plan; `done` says who marked it done, and when."""

    id: uuid.UUID
    kind: NextStepKind
    description: str
    due_date: dt.date | None
    entered: Entered | None
    done: Done | None


LabFlag = Literal["low", "normal", "high", "critical"]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class NewLabResult(BaseModel):
    """One value of a panel: a number, or text for results that aren't a plain number (e.g. "<5")."""

    analyte: Short
    value: Decimal | None = None
    value_text: Short | None = None
    unit: Unit | None = None
    ref_low: Decimal | None = None
    ref_high: Decimal | None = None

    @model_validator(mode="after")
    def _has_a_value_and_a_sensible_range(self) -> "NewLabResult":
        if self.value is None and not self.value_text:
            raise ValueError("Each result needs a value.")
        if self.ref_low is not None and self.ref_high is not None and self.ref_low > self.ref_high:
            raise ValueError("A reference range's low can't be above its high.")
        return self


class NewLabPanel(BaseModel):
    """Bloods entered as a panel: one save, one Verification."""

    collected_on: dt.date
    collected_time: dt.time | None = None
    panel: Short | None = None
    results: list[NewLabResult] = Field(min_length=1, max_length=60)


class LabResultChange(BaseModel):
    analyte: Short | None = None
    value: Decimal | None = None
    value_text: Short | None = None
    unit: Unit | None = None
    ref_low: Decimal | None = None
    ref_high: Decimal | None = None
    reason: Reason


class LabResultRow(BaseModel):
    id: uuid.UUID
    panel_id: uuid.UUID | None
    panel: str | None
    analyte: str
    value: Decimal | None
    value_text: str | None
    unit: str | None
    ref_low: Decimal | None
    ref_high: Decimal | None
    # From the reference range entered with it (none without a range or a number).
    flag: LabFlag | None
    collected_at: dt.datetime
    entered: Entered | None


class LabPanelRow(BaseModel):
    panel_id: uuid.UUID
    panel: str | None
    collected_at: dt.datetime
    results: list[LabResultRow]


# --- Treatment Courses (#40) ------------------------------------------------------------------------------

Modality = Literal["systemic", "surgery", "radiation"]
Intent = Literal["curative", "neoadjuvant", "adjuvant", "palliative"]
Detail = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class RegimenDrug(BaseModel):
    """One planned drug of a Regimen, with its planned dose (e.g. "60 mg/m2")."""

    drug: Short
    dose: Detail | None = None


class TreatmentCourseFields(BaseModel):
    intent: Intent | None = None
    regimen_name: Short | None = None
    regimen_drugs: list[RegimenDrug] = []
    start_date: dt.date | None = None
    # None: ongoing. Set only when a User records that the course ended.
    end_date: dt.date | None = None
    reason_stopped: Detail | None = None
    # Surgery: procedure, margins; radiation: site, dose, fractions.
    details: dict[Short, Detail] | None = None


class NewTreatmentCourse(TreatmentCourseFields):
    condition_id: uuid.UUID
    modality: Modality

    @model_validator(mode="after")
    def _consistent(self) -> "NewTreatmentCourse":
        if self.modality != "systemic" and (self.regimen_name or self.regimen_drugs):
            raise ValueError("Only a systemic course has a Regimen.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("A course can't end before it starts.")
        return self


class TreatmentCourseChange(BaseModel):
    """Only the fields that change, and why (e.g. recording that it ended)."""

    intent: Intent | None = None
    regimen_name: Short | None = None
    regimen_drugs: list[RegimenDrug] | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    reason_stopped: Detail | None = None
    details: dict[Short, Detail] | None = None
    reason: Reason


class TreatmentCourseRow(TreatmentCourseFields):
    id: uuid.UUID
    condition_id: uuid.UUID
    condition_name: str
    modality: Modality
    ongoing: bool
    entered: Entered | None
