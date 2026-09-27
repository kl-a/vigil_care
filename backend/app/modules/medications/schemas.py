import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.audit.schemas import Reason
from app.modules.clinical.schemas import Entered


class DrugOption(BaseModel):
    """A drug the Medication Manager can pick, from the drug reference."""

    id: uuid.UUID
    generic_name: str
    brand_names: list[str]
    atc_code: str | None
    is_cancer_drug: bool
    # Its PBS Items in the current schedule; any of them opens the drug in the PBS Drug Lookup.
    pbs_item_codes: list[str]


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Frequency = Literal["daily", "twice_daily", "three_times_daily", "weekly", "fortnightly", "monthly", "prn", "stat", "other"]
Route = Literal["oral", "iv", "subcut", "im", "topical", "inhaled", "pr", "other"]
Category = Literal["cancer_treatment", "supportive_care", "comorbidity_management", "supplement", "other"]
MedicationStatus = Literal["active", "discontinued", "on_hold", "completed", "unknown"]
# Changed by hand; a Medication is discontinued only by stopping it (with the date and why).
SettableStatus = Literal["active", "on_hold", "completed", "unknown"]
# Where a hand-entered Medication came from; `document_extracted` is for extraction (Stage 6).
EnteredSource = Literal["doctor_entered", "patient_reported", "pharmacy_list"]
ChangeType = Literal["added", "dose_changed", "discontinued", "restarted", "status_changed", "verified", "corrected"]
PositiveDose = Annotated[Decimal, Field(gt=0)]


class MedicationFields(BaseModel):
    brand_name: Text | None = None
    dose_amount: PositiveDose | None = None
    dose_unit: Text | None = None
    frequency: Frequency | None = None
    frequency_detail: Text | None = None
    route: Route | None = None
    indication: Text | None = None
    category: Category | None = None
    start_date: dt.date | None = None
    prescribed_by_provider_id: uuid.UUID | None = None
    # A cancer drug's Treatment Course (e.g. one drug of a Regimen).
    treatment_course_id: uuid.UUID | None = None
    notes: Notes | None = None


class NewMedication(MedicationFields):
    """Picked from the drug reference, or free text (`drug_name`) when it isn't in it."""

    drug_reference_id: uuid.UUID | None = None
    drug_name: Text | None = None
    status: SettableStatus = "active"
    source: EnteredSource = "doctor_entered"

    @model_validator(mode="after")
    def _names_a_drug(self) -> "NewMedication":
        if self.drug_reference_id is None and not self.drug_name:
            raise ValueError("Pick a drug from the drug reference, or type its name.")
        return self


class MedicationChange(MedicationFields):
    """Only the fields that change, and why (once for the whole save)."""

    status: SettableStatus | None = None
    reason: Reason


class Stop(BaseModel):
    end_date: dt.date
    reason: Reason


class Restart(BaseModel):
    reason: Reason


class MedicationRow(MedicationFields):
    id: uuid.UUID
    drug_reference_id: uuid.UUID | None
    # As entered: the drug reference's generic name, or the free text.
    drug_name: str
    generic_name: str | None
    in_drug_reference: bool
    is_cancer_drug: bool
    # Open the drug in the PBS Drug Lookup; none when it isn't in the drug reference.
    pbs_item_codes: list[str]
    dose_display: str | None
    status: MedicationStatus
    end_date: dt.date | None
    reason_discontinued: str | None
    prescriber_name: str | None
    treatment_course_name: str | None
    source: str
    entered: Entered | None


class MedicationChangeRow(BaseModel):
    """One entry of the change log: what changed, who changed it, when and why."""

    id: uuid.UUID
    medication_id: uuid.UUID
    drug_name: str
    change_type: ChangeType
    previous_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    by: str
    at: dt.datetime
    reason: str | None
