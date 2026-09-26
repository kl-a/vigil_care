import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel

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
    entered: Entered | None
