import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.core.fields import Email, Text
from app.modules.practice.models import ProviderSpecialty



class PracticeDetails(BaseModel):
    """The Practice's details (design doc §5 screen 19). Its locations are its Sites."""

    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    fax: str | None
    email: str | None
    abn: str | None


class PracticeChange(BaseModel):
    """Only the fields sent are changed. Empty text clears an optional field."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    address: Text | None = None
    phone: Text | None = None
    fax: Text | None = None
    email: Email | None = None
    abn: Text | None = None

    @field_validator("abn")
    @classmethod
    def _abn_has_eleven_digits(cls, value: str | None) -> str | None:
        if value and len("".join(ch for ch in value if ch.isdigit())) != 11:
            raise ValueError("An ABN has 11 digits.")
        return value


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]


class SiteRow(BaseModel):
    """A place where the Practice sees Patients (#25). Trial-site distances are measured from it."""

    id: uuid.UUID
    name: str
    address: str | None
    lat: float | None
    lng: float | None
    is_primary: bool


class NewSite(BaseModel):
    """The first Site is the primary; another becomes primary by choosing it (`SiteChange`)."""

    name: Name
    address: Text | None = None
    lat: Latitude | None = None
    lng: Longitude | None = None


class SiteChange(BaseModel):
    """Only the fields sent are changed. The primary is moved by choosing another Site, never unset."""

    name: Name | None = None
    address: Text | None = None
    lat: Latitude | None = None
    lng: Longitude | None = None
    is_primary: Literal[True] | None = None


class ProviderRow(BaseModel):
    """A clinician in the Practice's directory (#7): internal, or an external referrer, specialist or contact."""

    id: uuid.UUID
    display_name: str
    title: str | None
    first_name: str
    last_name: str
    provider_number: str | None
    specialty: ProviderSpecialty
    is_internal: bool
    organisation: str | None
    phone: str | None
    email: str | None
    fax: str | None
    notes: str | None


class NewProvider(BaseModel):
    title: Text | None = None
    first_name: Name
    last_name: Name
    provider_number: Text | None = None
    specialty: ProviderSpecialty
    is_internal: bool = False
    organisation: Text | None = None
    phone: Text | None = None
    email: Email | None = None
    fax: Text | None = None
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class ProviderChange(BaseModel):
    """Only the fields sent are changed. Empty text clears an optional field."""

    title: Text | None = None
    first_name: Name | None = None
    last_name: Name | None = None
    provider_number: Text | None = None
    specialty: ProviderSpecialty | None = None
    is_internal: bool | None = None
    organisation: Text | None = None
    phone: Text | None = None
    email: Email | None = None
    fax: Text | None = None
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
