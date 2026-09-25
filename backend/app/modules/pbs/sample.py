"""The bundled sample of the PBS Schedule (design doc §15 Stage 3): a few oncology drugs, including
pembrolizumab, so demos work offline. A Refresh loads it only when the PBS Schedule API can't be reached and
Vigil has no schedule from the API yet; it's marked as sample data wherever it's shown. Not for clinical use.

sample_schedule.json is an extract of the public PBS Schedule (1 September 2026), normalised by the API
client, with the Department of Health's copyright statement kept as the licence requires.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.modules.pbs.schedule import Copayments, Listing, Schedule, ScheduleItem, ScheduleRef

SAMPLE = Path(__file__).with_name("sample_schedule.json")


class SampleSchedule:
    """A ScheduleSource that never needs the network."""

    def __init__(self, path: Path = SAMPLE) -> None:
        self._path = path

    def current(self) -> ScheduleRef:
        return ScheduleRef(schedule_code=0, schedule_date=date.fromisoformat(self._read()["schedule_date"]))

    def fetch(self, ref: ScheduleRef) -> Schedule:
        sample = self._read()
        copayments = sample["copayments"]
        return Schedule(
            schedule_date=date.fromisoformat(sample["schedule_date"]),
            copayments=Copayments(
                general=Decimal(str(copayments["general"])),
                concessional=Decimal(str(copayments["concessional"])),
                safety_net_general=_decimal(copayments.get("safety_net_general")),
                safety_net_concessional=_decimal(copayments.get("safety_net_concessional")),
            ),
            items=tuple(_item(item) for item in sample["items"]),
            source="sample",
        )

    def _read(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(self._path.read_text(encoding="utf-8"))
        return data


def _item(item: dict[str, Any]) -> ScheduleItem:
    listings = tuple(
        Listing(
            indication=listing["indication"],
            level=listing["level"],
            restriction_code=listing["restriction_code"],
            treatment_phase=listing.get("treatment_phase"),
            conditions=tuple(listing.get("conditions", ())),
        )
        for listing in item.get("listings", ())
    )
    return ScheduleItem(
        item_code=item["item_code"],
        drug_name=item["drug_name"],
        restriction_level=item["restriction_level"],
        brand_names=tuple(item.get("brand_names", ())),
        form=item.get("form"),
        program_code=item.get("program_code"),
        listings=listings,
        max_quantity=item.get("max_quantity"),
        max_amount=_decimal(item.get("max_amount")),
        amount_unit=item.get("amount_unit"),
        repeats=item.get("repeats"),
    )


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))
