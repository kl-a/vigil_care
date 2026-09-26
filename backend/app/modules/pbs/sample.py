"""The Sample Schedule (CONTEXT.md, design doc §10.2): a full copy of one past PBS Schedule, bundled so demos
work offline. A Refresh loads it only when the PBS Schedule API can't be reached (or there's no API key) and
Vigil has no schedule from the API yet. It is out of date by design: marked as sample data, for demos only,
wherever it's shown. Never for clinical use.

sample_schedule.json.gz is the PBS Schedule of 1 September 2026, normalised by the API client and written by
`scripts/pbs_snapshot.py`, with the Department of Health's copyright statement kept as the licence requires.
Each restriction's text is stored once and referenced by the items it applies to.
"""

import gzip
import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.modules.pbs.schedule import Copayments, Listing, Schedule, ScheduleItem, ScheduleRef

SAMPLE = Path(__file__).with_name("sample_schedule.json.gz")
NOTICE = (
    "SAMPLE DATA, OUT OF DATE, FOR DEMOS ONLY: NOT FOR CLINICAL USE. A copy of the PBS Schedule of {date}, bundled "
    "so Vigil's demos work offline. Refresh from the PBS Schedule API for the current schedule."
)


class SampleSchedule:
    """A ScheduleSource that never needs the network."""

    def __init__(self, path: Path = SAMPLE) -> None:
        self._path = path

    def current(self) -> ScheduleRef:
        return ScheduleRef(schedule_code=0, schedule_date=date.fromisoformat(self._read()["schedule_date"]))

    def fetch(self, ref: ScheduleRef) -> Schedule:
        return from_json(self._read())

    def _read(self) -> dict[str, Any]:
        with gzip.open(self._path, "rt", encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
        return data


def to_json(schedule: Schedule, copyright_notice: list[str]) -> dict[str, Any]:
    """The Sample Schedule file's contents for `schedule`."""
    restrictions: dict[str, dict[str, Any]] = {}
    items = []
    for item in schedule.items:
        for listing in item.listings:
            restrictions[listing.restriction_code] = {
                "indication": listing.indication,
                "treatment_phase": listing.treatment_phase,
                "conditions": list(listing.conditions),
            }
        items.append({
            "item_code": item.item_code,
            "drug_name": item.drug_name,
            "brand_names": list(item.brand_names),
            "form": item.form,
            "program_code": item.program_code,
            "program_title": item.program_title,
            "atc_codes": list(item.atc_codes),
            "restriction_level": item.restriction_level,
            "max_quantity": item.max_quantity,
            "max_packs": item.max_packs,
            "pack_size": item.pack_size,
            "max_amount": None if item.max_amount is None else float(item.max_amount),
            "amount_unit": item.amount_unit,
            "repeats": item.repeats,
            # [restriction code, level]: a restriction's level can depend on the item.
            "listings": [[listing.restriction_code, listing.level] for listing in item.listings],
        })
    copayments = schedule.copayments
    return {
        "notice": NOTICE.format(date=schedule.schedule_date.isoformat()),
        "copyright": copyright_notice,
        "schedule_date": schedule.schedule_date.isoformat(),
        "copayments": {
            "general": float(copayments.general),
            "concessional": float(copayments.concessional),
            "safety_net_general": _float(copayments.safety_net_general),
            "safety_net_concessional": _float(copayments.safety_net_concessional),
        },
        "restrictions": restrictions,
        "items": items,
    }


def from_json(sample: Mapping[str, Any]) -> Schedule:
    copayments = sample["copayments"]
    return Schedule(
        schedule_date=date.fromisoformat(sample["schedule_date"]),
        copayments=Copayments(
            general=Decimal(str(copayments["general"])),
            concessional=Decimal(str(copayments["concessional"])),
            safety_net_general=_decimal(copayments.get("safety_net_general")),
            safety_net_concessional=_decimal(copayments.get("safety_net_concessional")),
        ),
        items=tuple(_item(item, sample["restrictions"]) for item in sample["items"]),
        source="sample",
    )


def _item(item: Mapping[str, Any], restrictions: Mapping[str, Mapping[str, Any]]) -> ScheduleItem:
    listings = tuple(
        Listing(
            indication=restrictions[code]["indication"],
            level=level,
            restriction_code=code,
            treatment_phase=restrictions[code].get("treatment_phase"),
            conditions=tuple(restrictions[code].get("conditions", ())),
        )
        for code, level in item.get("listings", ())
    )
    return ScheduleItem(
        item_code=item["item_code"],
        drug_name=item["drug_name"],
        restriction_level=item["restriction_level"],
        brand_names=tuple(item.get("brand_names", ())),
        form=item.get("form"),
        program_code=item.get("program_code"),
        program_title=item.get("program_title"),
        atc_codes=tuple(item.get("atc_codes", ())),
        listings=listings,
        max_quantity=item.get("max_quantity"),
        max_packs=item.get("max_packs"),
        pack_size=item.get("pack_size"),
        max_amount=_decimal(item.get("max_amount")),
        amount_unit=item.get("amount_unit"),
        repeats=item.get("repeats"),
    )


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)
