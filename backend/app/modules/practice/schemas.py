import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


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
    email: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+)?$")] | None = None
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
