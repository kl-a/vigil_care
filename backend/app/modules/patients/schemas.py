import uuid
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


def _digits(count: int, what: str) -> AfterValidator:
    def check(value: str) -> str:
        digits = [ch for ch in value if ch.isdigit()]
        if value and (len(digits) != count or any(ch not in "0123456789 " for ch in value)):
            raise ValueError(f"{what} has {count} digits.")
        return value

    return AfterValidator(check)


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("A date of birth can't be in the future.")
    return value


MedicareNumber = Annotated[str, StringConstraints(strip_whitespace=True), _digits(10, "A Medicare number")]
Ihi = Annotated[str, StringConstraints(strip_whitespace=True), _digits(16, "An IHI")]
Irn = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[1-9]?$")]
Email = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+)?$")]
Dob = Annotated[date, AfterValidator(_not_in_future)]


class PatientIdentity(BaseModel):
    """Who the Patient is, shown in full inside Vigil and never sent outside the Practice Boundary (§9.3)."""

    given_name: str
    family_name: str
    dob: date | None
    medicare_number: str | None
    medicare_irn: str | None
    ihi: str | None
    mrn: str | None
    address: str | None
    phone: str | None
    mobile: str | None
    email: str | None
    next_of_kin_name: str | None
    next_of_kin_phone: str | None


class NewPatient(BaseModel):
    """A new Patient's identity. The Pseudonym is assigned, never chosen."""

    given_name: Name
    family_name: Name
    dob: Dob | None = None
    medicare_number: MedicareNumber | None = None
    medicare_irn: Irn | None = None
    ihi: Ihi | None = None
    mrn: Text | None = None
    address: Text | None = None
    phone: Text | None = None
    mobile: Text | None = None
    email: Email | None = None
    next_of_kin_name: Text | None = None
    next_of_kin_phone: Text | None = None


class IdentityChange(BaseModel):
    """Only the fields sent are changed. Empty text clears an optional field; names can't be cleared."""

    given_name: Name | None = None
    family_name: Name | None = None
    dob: Dob | None = None
    medicare_number: MedicareNumber | None = None
    medicare_irn: Irn | None = None
    ihi: Ihi | None = None
    mrn: Text | None = None
    address: Text | None = None
    phone: Text | None = None
    mobile: Text | None = None
    email: Email | None = None
    next_of_kin_name: Text | None = None
    next_of_kin_phone: Text | None = None


class PatientRow(BaseModel):
    """A Patient in the Patient List. Cancer Types and counts join in later stages."""

    id: uuid.UUID
    pseudonym: str
    display_name: str
    dob: date | None
    mrn: str | None
    updated_at: datetime


class IdentityHistoryEntry(BaseModel):
    """One change to the Patient's identity: who, their Job Title then, what changed and when."""

    action: str
    by_display_name: str
    by_job_title: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    at: datetime


class PatientDetail(BaseModel):
    """The Patient header and Overview's identity card, with the identity's audit trail (newest first)."""

    id: uuid.UUID
    pseudonym: str
    display_name: str
    identity: PatientIdentity
    history: list[IdentityHistoryEntry]
