"""PBS Drug Lookup (#20, design doc §5 screen 14): search the current PBS Schedule by drug, brand or active
ingredient, and read a drug's items with their Listing per indication. Staff only, never developer admins.
The schedule is loaded by a PBS Refresh replaying the recorded API fixture.
"""

import uuid
from collections.abc import Callable

import pytest

from app.db.provision import DatabaseSettings
from tests.api.conftest import SignIn
from tests.db.seed import Seed
from tests.fixtures.pbs import PbsRefresher, RecordedPbsApi, clear_pbs

Refresh = Callable[..., None]


@pytest.fixture
def refresh(database: DatabaseSettings, committed: Seed) -> Refresh:
    """Starts from no PBS data; each call runs one Refresh (`down=("*",)`: the API is unreachable)."""
    clear_pbs(database)
    kind = f"test_refresh_pbs_{uuid.uuid4().hex[:8]}"
    committed.insert("job_kind", key=kind, description="Test PBS Refresh")

    def run(down: tuple[str, ...] = ()) -> None:
        PbsRefresher(database, kind, RecordedPbsApi(down=down)).run()

    return run


def test_search_finds_a_drug_by_name_brand_active_ingredient_or_item_code(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("clinician")
    for q in ("pembro", "Keytruda", "PEMBROLIZUMAB", "12120x"):
        [found] = client.get("/pbs/drugs", params={"q": q}).json()
        assert found["drug_name"] == "Pembrolizumab", q
    [pembrolizumab] = client.get("/pbs/drugs", params={"q": "pembrolizumab"}).json()
    assert pembrolizumab["brand_names"] == ["Keytruda"]
    assert pembrolizumab["item_count"] == 14
    assert client.get("/pbs/drugs", params={"q": "rifaximin"}).json() == []  # not oncology: never loaded
    assert client.get("/pbs/drugs", params={"q": " "}).json() == []


def test_a_drug_shows_each_item_with_its_listing_per_indication_co_payments_and_schedule_date(
    sign_in: SignIn, refresh: Refresh
) -> None:
    refresh()
    client, _ = sign_in("secretary")
    drug = client.get("/pbs/drugs/12120X").json()
    assert (drug["drug_name"], drug["schedule_date"], len(drug["items"])) == ("Pembrolizumab", "2026-09-01", 14)
    item = next(i for i in drug["items"] if i["item_code"] == "12120X")
    assert item["form"] == "pembrolizumab 100 mg/4 mL injection, 4 mL vial"
    assert (item["max_amount"], item["amount_unit"], item["repeats"]) == (200, "mg", 7)
    assert (item["copay_general"], item["copay_concessional"]) == (25, 7.7)
    listing = item["listings"][0]
    assert listing["indication"] == "Stage IIIB, Stage IIIC or Stage IIID malignant melanoma"
    assert listing["level"] == "authority_required"
    assert listing["treatment_phase"] == "Initial treatment - 3 weekly treatment regimen"
    assert "The treatment must be in addition to complete surgical resection; AND" in listing["conditions"]

    carboplatin = client.get("/pbs/drugs/" + client.get("/pbs/drugs", params={"q": "carboplatin"}).json()[0]["item_code"]).json()
    assert all(i["restriction_level"] == "unrestricted" and i["listings"] == [] for i in carboplatin["items"])
    assert client.get("/pbs/drugs/99999Z").status_code == 404


def test_the_schedule_says_as_of_when_and_from_where(sign_in: SignIn, refresh: Refresh) -> None:
    client, _ = sign_in("trial_coordinator")
    empty = client.get("/pbs/schedule").json()
    assert (empty["schedule_date"], empty["current"], empty["last_refresh"]) == (None, None, None)

    refresh()
    status = client.get("/pbs/schedule").json()
    assert (status["schedule_date"], status["is_sample"], status["item_count"]) == ("2026-09-01", False, 18)
    assert (status["safety_net_general"], status["safety_net_concessional"]) == (1748.2, 277.2)
    assert status["last_refresh"]["status"] == "succeeded"


def test_after_a_failed_refresh_the_previous_schedule_stays_with_a_warning(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    refresh(down=("*",))
    client, _ = sign_in("clinician")
    status = client.get("/pbs/schedule").json()
    assert (status["current"]["status"], status["current"]["source"]) == ("succeeded", "pbs_api")
    assert status["last_refresh"]["status"] == "failed"
    assert status["schedule_date"] == "2026-09-01"
    assert client.get("/pbs/drugs", params={"q": "pembrolizumab"}).json()[0]["item_count"] == 14


def test_the_bundled_sample_is_marked_as_sample_data(sign_in: SignIn, refresh: Refresh) -> None:
    refresh(down=("*",))
    client, _ = sign_in("clinician")
    status = client.get("/pbs/schedule").json()
    assert status["is_sample"] is True
    assert (status["current"]["status"], status["current"]["source"]) == ("partial", "sample")
    [pembrolizumab] = client.get("/pbs/drugs", params={"q": "pembrolizumab"}).json()
    drug = client.get(f"/pbs/drugs/{pembrolizumab['item_code']}").json()
    assert all(item["listings"] for item in drug["items"])


def test_developer_admins_have_no_pbs_lookup(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("developer_admin")
    for path in ("/pbs/schedule", "/pbs/drugs?q=pembro", "/pbs/drugs/12120X"):
        assert client.get(path).status_code == 403, path
