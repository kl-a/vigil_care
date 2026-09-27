"""The drug reference built from the PBS Schedule (#36, design doc §6.3): Shared Reference Data the Medication
Manager picks from. Each PBS Refresh rebuilds it, as its own step; drugs that leave the Schedule are no longer
offered. Refreshes replay the recorded PBS API fixture.
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest

from app.db.provision import DatabaseSettings
from tests.api.conftest import SignIn
from tests.db.seed import Seed
from tests.fixtures.pbs import PbsRefresher, RecordedPbsApi, clear_pbs

Refresh = Callable[..., Any]


@pytest.fixture
def refresh(database: DatabaseSettings, committed: Seed) -> Refresh:
    clear_pbs(database)
    kind = f"test_refresh_pbs_{uuid.uuid4().hex[:8]}"
    committed.insert("job_kind", key=kind, description="Test PBS Refresh")

    def run(down: tuple[str, ...] = ()) -> Any:
        return PbsRefresher(database, kind, RecordedPbsApi(down=down)).run()

    return run


def drugs(committed: Seed) -> dict[str, dict[str, Any]]:
    rows = committed.conn.execute(
        "SELECT generic_name, brand_names, atc_code, is_cancer_drug, pbs_item_codes, in_current_schedule FROM drug_reference"
    ).fetchall()
    return {
        row[0]: {"brands": row[1], "atc": row[2], "cancer": row[3], "items": row[4], "current": row[5]}
        for row in rows
    }


def test_a_pbs_refresh_builds_the_drug_reference_as_its_own_step(refresh: Refresh, committed: Seed) -> None:
    job = refresh()
    assert [step.name for step in job.steps] == ["fetch", "store", "drug_reference"]
    assert job.steps[2].output == {"drug_count": 6}  # counts only: no Patient data, no drug names
    built = drugs(committed)
    assert set(built) == {"Carboplatin", "Dexamfetamine", "Duloxetine", "Letrozole", "Pembrolizumab", "Rifaximin"}
    pembrolizumab = built["Pembrolizumab"]
    assert (pembrolizumab["brands"], pembrolizumab["atc"], pembrolizumab["cancer"], pembrolizumab["current"]) == (
        ["Keytruda"], "L01FF02", True, True,
    )
    assert len(pembrolizumab["items"]) == 14 and "12120X" in pembrolizumab["items"]
    dexamfetamine = built["Dexamfetamine"]
    assert (dexamfetamine["atc"], dexamfetamine["cancer"], dexamfetamine["items"]) == ("N06BA02", False, ["1165H"])
    assert built["Letrozole"]["cancer"] is True  # L02: endocrine therapy


def test_a_later_refresh_rebuilds_it_and_retires_drugs_that_left_the_schedule(refresh: Refresh, committed: Seed) -> None:
    refresh()
    # As if rifaximin had been listed once but isn't in this schedule: it stays (Medications may point at it),
    # no longer offered.
    committed.conn.execute("UPDATE drug_reference SET generic_name = 'Oldmycin' WHERE generic_name = 'Rifaximin'")
    refresh()
    built = drugs(committed)
    assert built["Oldmycin"]["current"] is False
    assert built["Rifaximin"]["current"] is True
    assert sum(1 for drug in built.values() if drug["current"]) == 6


def test_the_sample_schedule_builds_it_too(refresh: Refresh, committed: Seed) -> None:
    refresh(down=("*",))
    built = drugs(committed)
    assert len(built) > 500 and built["Pembrolizumab"]["cancer"] is True


def test_staff_search_the_drug_reference_by_generic_or_brand_name(refresh: Refresh, sign_in: SignIn) -> None:
    refresh()
    client, _ = sign_in("secretary")
    for q in ("pembro", "KEYTRUDA"):
        [found] = client.get("/drugs", params={"q": q}).json()
        assert "12120X" in found["pbs_item_codes"] and len(found["pbs_item_codes"]) == 14
        assert found | {"id": None} == {
            "id": None, "generic_name": "Pembrolizumab", "brand_names": ["Keytruda"], "atc_code": "L01FF02",
            "is_cancer_drug": True, "pbs_item_codes": found["pbs_item_codes"],
        }
    assert [d["generic_name"] for d in client.get("/drugs", params={"q": "e"}).json()][:3] == ["Dexamfetamine", "Duloxetine", "Letrozole"]
    assert client.get("/drugs", params={"q": ""}).json() == []


def test_drugs_no_longer_in_the_schedule_are_not_offered(refresh: Refresh, sign_in: SignIn, committed: Seed) -> None:
    refresh()
    committed.conn.execute("UPDATE drug_reference SET in_current_schedule = false WHERE generic_name = 'Rifaximin'")
    client, _ = sign_in("clinician")
    assert client.get("/drugs", params={"q": "rifaximin"}).json() == []


def test_developer_admins_have_no_drug_search(refresh: Refresh, sign_in: SignIn) -> None:
    client, _ = sign_in("developer_admin")
    assert client.get("/drugs", params={"q": "pembro"}).status_code == 403
