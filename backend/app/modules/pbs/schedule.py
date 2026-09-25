"""The PBS Schedule as Vigil keeps it (design doc §10.2), and where a Refresh gets it from.

A `ScheduleSource` is the PBS Schedule API (`api_client.py`) or the bundled sample (`sample.py`); tests give
the API client a recorded fixture, never the live service.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Protocol


class SourceUnreachable(Exception):
    """The PBS Schedule API couldn't be reached or refused us. `code` is short and IDs-only (a Job error)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Listing:
    """An item's PBS listing for one indication (one PBS restriction)."""

    indication: str
    level: str  # one of models.RESTRICTION_LEVELS
    restriction_code: str
    treatment_phase: str | None = None
    # The prescribing conditions, one paragraph each.
    conditions: tuple[str, ...] = ()

    def as_json(self) -> dict[str, Any]:
        return {
            "indication": self.indication,
            "treatment_phase": self.treatment_phase,
            "level": self.level,
            "restriction_code": self.restriction_code,
            "conditions": list(self.conditions),
        }


@dataclass(frozen=True)
class ScheduleItem:
    item_code: str
    drug_name: str
    restriction_level: str  # one of models.RESTRICTION_LEVELS
    brand_names: tuple[str, ...] = ()
    form: str | None = None
    program_code: str | None = None
    listings: tuple[Listing, ...] = ()
    max_quantity: int | None = None
    max_amount: Decimal | None = None
    amount_unit: str | None = None
    repeats: int | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class Copayments:
    """Patient co-payments and PBS Safety Net thresholds; the same for every item in a schedule."""

    general: Decimal
    concessional: Decimal
    safety_net_general: Decimal | None = None
    safety_net_concessional: Decimal | None = None


@dataclass(frozen=True)
class Schedule:
    schedule_date: date
    copayments: Copayments
    items: tuple[ScheduleItem, ...]
    # Items the source listed but Vigil couldn't read (e.g. an unknown benefit type): the Refresh is partial.
    skipped: int = 0
    source: str = "pbs_api"  # or "sample"


@dataclass(frozen=True)
class ScheduleRef:
    """Which schedule is current at the source."""

    schedule_code: int
    schedule_date: date


class ScheduleSource(Protocol):
    def current(self) -> ScheduleRef:
        """The current schedule. Raises SourceUnreachable."""
        ...

    def fetch(self, ref: ScheduleRef) -> Schedule:
        """Every oncology-relevant item in the schedule. Raises SourceUnreachable."""
        ...

