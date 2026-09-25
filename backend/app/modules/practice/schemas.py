import uuid
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class PracticeDetails(BaseModel):
    """The Practice's details (design doc §5 screen 19). Location is for trial-site distances."""

    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    fax: str | None
    email: str | None
    abn: str | None
    lat: float | None
    lng: float | None


class PracticeChange(BaseModel):
    """Only the fields sent are changed. Empty text clears an optional field."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    address: Text | None = None
    phone: Text | None = None
    fax: Text | None = None
    email: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+)?$")] | None = None
    abn: Text | None = None
    lat: Annotated[float, Field(ge=-90, le=90)] | None = None
    lng: Annotated[float, Field(ge=-180, le=180)] | None = None

    @field_validator("abn")
    @classmethod
    def _abn_has_eleven_digits(cls, value: str | None) -> str | None:
        if value and len("".join(ch for ch in value if ch.isdigit())) != 11:
            raise ValueError("An ABN has 11 digits.")
        return value
