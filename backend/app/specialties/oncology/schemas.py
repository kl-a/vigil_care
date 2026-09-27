import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.audit.schemas import Reason
from app.modules.clinical.schemas import Entered
from app.modules.clinical.schemas import Name as Text
DiseaseExtent = Literal["localised", "locally_advanced", "metastatic", "unknown"]
CancerStatus = Literal["active", "no_evidence_of_disease", "unknown"]


class CancerTypeOption(BaseModel):
    """A Cancer Type (site + histology, no subtypes), keyed to MeSH so it matches the trial registries."""

    key: str
    display_name: str
    mesh_term: str | None
    mesh_id: str | None
    staging_systems: list[str]


class NewCancerDiagnosis(BaseModel):
    """A primary cancer: a Condition, extended by Oncology. `name` defaults to the Cancer Type's name."""

    cancer_type: str
    name: Text | None = None
    histology: Text | None = None
    primary_site: Text | None = None
    laterality: Text | None = None
    dx_date: dt.date | None = None
    stage_system: Text | None = None
    # At diagnosis; never updated as the disease changes (only corrected).
    stage: Text | None = None
    disease_extent: DiseaseExtent = "unknown"
    disease_extent_as_of: dt.date | None = None
    cancer_status: CancerStatus = "unknown"


class CancerDiagnosisChange(BaseModel):
    """Only the fields that change, and why (once for the whole save). Clinicians only."""

    name: Text | None = None
    histology: Text | None = None
    primary_site: Text | None = None
    laterality: Text | None = None
    dx_date: dt.date | None = None
    stage_system: Text | None = None
    stage: Text | None = None
    disease_extent: DiseaseExtent | None = None
    disease_extent_as_of: dt.date | None = None
    cancer_status: CancerStatus | None = None
    reason: Reason


class CancerDiagnosisRow(BaseModel):
    id: uuid.UUID
    condition_id: uuid.UUID
    name: str
    cancer_type: CancerTypeOption
    histology: str | None
    primary_site: str | None
    laterality: str | None
    dx_date: dt.date | None
    stage_system: str | None
    stage: str | None
    disease_extent: DiseaseExtent
    disease_extent_as_of: dt.date | None
    cancer_status: CancerStatus
    current_biomarkers: list["BiomarkerChip"] = []
    entered: Entered | None


# --- ECOG and CNS status (#44) ----------------------------------------------------------------------------

PerformanceScale = Literal["ECOG", "KPS"]


class NewPerformanceStatus(BaseModel):
    """ECOG 0–5, or KPS 0–100 in steps of 10."""

    scale: PerformanceScale = "ECOG"
    value: int
    assessed_on: dt.date

    @model_validator(mode="after")
    def _in_scale(self) -> "NewPerformanceStatus":
        if self.scale == "ECOG" and not 0 <= self.value <= 5:
            raise ValueError("ECOG is 0 to 5.")
        if self.scale == "KPS" and not (0 <= self.value <= 100 and self.value % 10 == 0):
            raise ValueError("KPS is 0 to 100, in steps of 10.")
        return self


class PerformanceStatusRow(BaseModel):
    id: uuid.UUID
    scale: PerformanceScale
    value: int
    assessed_on: dt.date
    entered: Entered | None


class CnsFields(BaseModel):
    present: bool | None = None
    lesion_count: Annotated[int, Field(ge=0)] | None = None
    locations: list[Text] = []
    treated: bool | None = None
    treatment_type: Text | None = None
    symptomatic: bool | None = None
    on_steroids: bool | None = None
    steroid_dose_mg: Annotated[Decimal, Field(ge=0)] | None = None
    leptomeningeal: bool | None = None


class NewCnsStatus(CnsFields):
    assessed_on: dt.date


class CnsStatusChange(CnsFields):
    """Only the fields that change, and why."""

    locations: list[Text] | None = None  # type: ignore[assignment]
    assessed_on: dt.date | None = None
    reason: Reason


class CnsStatusRow(CnsFields):
    id: uuid.UUID
    assessed_on: dt.date
    entered: Entered | None


# --- Biomarkers (#38) -------------------------------------------------------------------------------------

BiomarkerMethod = Literal["NGS", "FISH", "IHC", "PCR", "ctDNA"]
SpecimenKind = Literal["primary", "metastasis", "liquid_biopsy"]


class NewBiomarker(BaseModel):
    """One result, never overwritten: a wrong one is removed (with why) and entered again."""

    name: Text
    variant: Text | None = None
    # The result category as reported, e.g. positive, negative, equivocal, low, detected.
    result: Text | None = None
    value_num: Decimal | None = None
    value_unit: Text | None = None
    method: BiomarkerMethod | None = None
    specimen_site: Text | None = None
    specimen_kind: SpecimenKind | None = None
    collected_on: dt.date | None = None
    reported_on: dt.date | None = None


class BiomarkerRow(NewBiomarker):
    id: uuid.UUID
    # The latest result of its Biomarker and variant.
    current: bool
    # Differing Biomarker Results: its Biomarker and variant has results in more than one category.
    differs: bool
    entered: Entered | None


class BiomarkerChip(BaseModel):
    """The current result of one Biomarker (and variant), for the Cancer Diagnosis's chips."""

    name: str
    variant: str | None
    result: str | None
    value_num: Decimal | None
    value_unit: str | None
    differs: bool


class BiomarkerMove(BaseModel):
    """Move a result to another of the Patient's Cancer Diagnoses (e.g. a new primary). Clinicians only."""

    cancer_diagnosis_id: uuid.UUID
    reason: Reason


# --- Recurrences (#39) ------------------------------------------------------------------------------------

RecurrenceStatus = Literal["suspected", "confirmed", "reclassified_as_new_primary", "ruled_out"]
RecurrenceExtent = Literal["local", "regional", "distant"]


class NewRecurrence(BaseModel):
    """Recorded as suspected; a clinician resolves it."""

    detected_on: dt.date | None = None
    extent: RecurrenceExtent | None = None
    sites: list[Text] = []


class Resolved(BaseModel):
    """Who resolved a Suspected Recurrence, and when."""

    by: str
    at: dt.datetime


class RecurrenceRow(NewRecurrence):
    id: uuid.UUID
    cancer_diagnosis_id: uuid.UUID
    cancer_diagnosis_name: str
    status: RecurrenceStatus
    new_cancer_diagnosis_id: uuid.UUID | None
    resolved: Resolved | None
    # Why it was ruled out (the clinician's reason).
    ruled_out_reason: str | None = None
    entered: Entered | None


class RuleOut(BaseModel):
    reason: Reason


# --- Line of Therapy (#40) --------------------------------------------------------------------------------


class LineOfTherapy(BaseModel):
    """A palliative systemic course's Line of Therapy: derived by start date, unless a clinician set it."""

    treatment_course_id: uuid.UUID
    cancer_diagnosis_id: uuid.UUID
    line: int
    overridden: bool
    # Why this number, e.g. "2nd line: 2nd palliative systemic course of Breast cancer".
    explanation: str


class LineOverride(BaseModel):
    """Set a course's line (None: derive it again), and why. Clinicians only."""

    line: Annotated[int, Field(ge=1, le=20)] | None
    reason: Reason
