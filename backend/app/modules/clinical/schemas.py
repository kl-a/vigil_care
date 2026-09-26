import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

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
