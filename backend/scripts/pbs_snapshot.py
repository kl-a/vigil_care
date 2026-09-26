"""Takes a snapshot of the live PBS Schedule API (needs VIGIL_PBS_API_KEY in .env) and writes:

- the Sample Schedule (app/modules/pbs/sample_schedule.json.gz): the whole current schedule, normalised by the
  API client; and
- the tests' recorded API (tests/fixtures/pbs_api.json): the same responses, trimmed to a few drugs.

The API allows one request every 20 seconds, so this takes a few minutes.

    cd backend && .venv/bin/python -m scripts.pbs_snapshot
"""

import gzip
import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.modules.pbs.api_client import HttpTransport, PbsApiClient
from app.modules.pbs.sample import SAMPLE, to_json

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pbs_api.json"
# Cancer drugs (one Unrestricted, one Restricted, one with Authority Required and Streamlined listings), and
# three that aren't: dexamfetamine (Authority Required), duloxetine (an antidepressant also used for pain) and
# rifaximin.
FIXTURE_DRUGS = {"Pembrolizumab", "Letrozole", "Carboplatin", "Dexamfetamine", "Duloxetine", "Rifaximin"}
# Tables trimmed to those drugs' items, by item code; restrictions are trimmed to the ones they use.
BY_ITEM = ("/items", "/item-atc-relationships", "/item-restriction-relationships")


class Recording:
    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport
        self.responses: list[dict[str, Any]] = []

    def __call__(self, path: str, params: Mapping[str, str | int]) -> Mapping[str, Any]:
        body = self._transport(path, params)
        self.responses.append({"path": path, "params": dict(params), "body": body})
        return body


def main() -> None:
    settings = Settings()
    recording = Recording(HttpTransport(settings.pbs_api_url, settings.pbs_api_key, settings.pbs_api_min_interval))
    client = PbsApiClient(recording)
    schedule = client.fetch(client.current())
    copyright_notice = recording.responses[0]["body"]["_meta"]["info"]["messages"][0]["content"]

    with gzip.open(SAMPLE, "wt", encoding="utf-8") as file:
        json.dump(to_json(schedule, copyright_notice), file, separators=(",", ":"))
    print(f"Sample Schedule: {len(schedule.items)} PBS Items, {SAMPLE.stat().st_size // 1024} KiB")

    FIXTURE.write_text(json.dumps(_fixture(recording.responses, schedule.schedule_date, copyright_notice), indent=1) + "\n")
    print(f"Recorded API: {FIXTURE}")


def _fixture(responses: list[dict[str, Any]], schedule_date: date, copyright_notice: list[str]) -> dict[str, Any]:
    codes = {
        row["pbs_code"] for response in responses if response["path"] == "/items"
        for row in response["body"]["data"] if row["drug_name"] in FIXTURE_DRUGS
    }
    restrictions = {
        row["res_code"] for response in responses if response["path"] == "/item-restriction-relationships"
        for row in response["body"]["data"] if row["pbs_code"] in codes
    }
    trimmed = []
    for response in responses:
        rows = response["body"]["data"]
        if response["path"] in BY_ITEM:
            rows = [row for row in rows if row["pbs_code"] in codes]
        elif response["path"] == "/restrictions":
            rows = [row for row in rows if row["res_code"] in restrictions]
        # The client pages by the table's total, so the recorded total is the live one.
        meta = {"total_records": response["body"]["_meta"]["total_records"]}
        trimmed.append({**response, "body": {"_meta": meta, "data": rows}})
    return {
        "about": (
            f"Recorded from the PBS Schedule API v3 on {date.today().isoformat()}, the schedule of "
            f"{schedule_date.isoformat()}, by scripts/pbs_snapshot.py. Each table is trimmed to "
            f"{', '.join(sorted(FIXTURE_DRUGS))}. Tests replay it; they never call the live service."
        ),
        "copyright": copyright_notice,
        "responses": trimmed,
    }


if __name__ == "__main__":
    main()
