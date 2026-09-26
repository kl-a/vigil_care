"""PBS Drug Lookup (#20, #30, design doc §5 screen 14): browse every drug in the current PBS Schedule, filter by
search, therapeutic group, program and listing type, and read a drug's items with their Listing per indication. Staff only, never developer admins.
The schedule is loaded by a PBS Refresh replaying the recorded API fixture.
"""

import uuid
from collections.abc import Callable
from typing import Any

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


def drug_names(page: dict[str, Any]) -> list[str]:
    return [drug["drug_name"] for drug in page["drugs"]]


def test_the_list_opens_with_every_drug_a_to_z(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("clinician")
    page = client.get("/pbs/drugs").json()
    assert drug_names(page) == ["Carboplatin", "Dexamfetamine", "Duloxetine", "Letrozole", "Pembrolizumab", "Rifaximin"]
    assert (page["total"], page["page"], page["page_size"]) == (6, 1, 50)

    dexamfetamine = page["drugs"][1]
    assert dexamfetamine["item_code"] == "1165H"
    assert dexamfetamine["forms"] == ["dexamfetamine sulfate 5 mg tablet, 100"]
    assert dexamfetamine["groups"] == [{"code": "N", "label": "Nervous system"}]
    assert dexamfetamine["levels"] == ["authority_required"]
    pembrolizumab = page["drugs"][4]
    assert (pembrolizumab["brand_names"], pembrolizumab["item_count"]) == (["Keytruda"], 14)
    assert pembrolizumab["levels"] == ["authority_required", "authority_required_streamlined"]


def test_the_list_pages(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("clinician")
    second = client.get("/pbs/drugs", params={"page": 2, "page_size": 4}).json()
    assert drug_names(second) == ["Pembrolizumab", "Rifaximin"]
    assert (second["total"], second["page"], second["page_size"]) == (6, 2, 4)
    assert client.get("/pbs/drugs", params={"page": 3, "page_size": 4}).json()["drugs"] == []


def test_search_finds_a_drug_by_name_brand_active_ingredient_or_item_code(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("clinician")
    for q in ("pembro", "Keytruda", "PEMBROLIZUMAB", "12120x"):
        assert drug_names(client.get("/pbs/drugs", params={"q": q}).json()) == ["Pembrolizumab"], q
    assert drug_names(client.get("/pbs/drugs", params={"q": "dexamfetamine"}).json()) == ["Dexamfetamine"]
    assert client.get("/pbs/drugs", params={"q": "no such drug"}).json()["total"] == 0


def test_filters_combine_and_a_drug_matches_when_any_of_its_items_does(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("clinician")

    def names(**filters: str) -> list[str]:
        return drug_names(client.get("/pbs/drugs", params=filters).json())

    assert names(group="cancer") == ["Carboplatin", "Letrozole", "Pembrolizumab"]
    assert names(group="N") == ["Dexamfetamine", "Duloxetine"]
    assert names(group="A") == ["Rifaximin"]
    assert names(program="GE") == ["Dexamfetamine", "Duloxetine", "Letrozole", "Rifaximin"]
    assert names(program="IP") == ["Carboplatin", "Pembrolizumab"]
    assert names(level="unrestricted") == ["Carboplatin"]
    assert names(level="restricted") == ["Duloxetine", "Letrozole"]
    # Streamlined on some of pembrolizumab's items or indications only.
    assert names(level="authority_required_streamlined") == ["Pembrolizumab"]
    assert names(group="N", level="authority_required") == ["Dexamfetamine"]
    assert names(q="dex", group="cancer") == []
    for unknown in ({"group": "Z"}, {"level": "free"}):
        assert client.get("/pbs/drugs", params=unknown).status_code == 422, unknown


def test_the_filter_options_come_from_the_current_schedule(sign_in: SignIn, refresh: Refresh) -> None:
    client, _ = sign_in("clinician")
    assert client.get("/pbs/filters").json() == {"groups": [], "programs": []}
    refresh()
    filters = client.get("/pbs/filters").json()
    assert filters["groups"] == [
        {"code": "cancer", "label": "Cancer drugs (ATC L01, L02)"},
        {"code": "A", "label": "Alimentary tract and metabolism"},
        {"code": "L", "label": "Antineoplastic and immunomodulating agents"},
        {"code": "N", "label": "Nervous system"},
    ]
    assert filters["programs"] == [
        {"code": "GE", "label": "General Schedule"},
        {"code": "IN", "label": "Section 100 (Efficient Funding of Chemotherapy) - Private Hospitals"},
        {"code": "IP", "label": "Section 100 (Efficient Funding of Chemotherapy) - Public Hospitals"},
    ]


def test_a_drug_shows_each_item_with_its_listing_per_indication_co_payments_and_schedule_date(
    sign_in: SignIn, refresh: Refresh
) -> None:
    refresh()
    client, _ = sign_in("secretary")
    drug = client.get("/pbs/drugs/12120X").json()
    assert (drug["drug_name"], drug["schedule_date"], len(drug["items"])) == ("Pembrolizumab", "2026-09-01", 14)
    assert drug["groups"] == [{"code": "L", "label": "Antineoplastic and immunomodulating agents"}]
    item = next(i for i in drug["items"] if i["item_code"] == "12120X")
    assert item["form"] == "pembrolizumab 100 mg/4 mL injection, 4 mL vial"
    assert item["program_title"] == "Section 100 (Efficient Funding of Chemotherapy) - Private Hospitals"
    assert (item["max_amount"], item["amount_unit"], item["repeats"]) == (200, "mg", 7)
    assert (item["copay_general"], item["copay_concessional"]) == (25, 7.7)
    listing = item["listings"][0]
    assert listing["indication"] == "Stage IIIB, Stage IIIC or Stage IIID malignant melanoma"
    assert listing["level"] == "authority_required"
    assert listing["treatment_phase"] == "Initial treatment - 3 weekly treatment regimen"
    assert "The treatment must be in addition to complete surgical resection; AND" in listing["conditions"]

    dexamfetamine = client.get("/pbs/drugs/1165h").json()["items"][0]
    assert (dexamfetamine["max_quantity"], dexamfetamine["max_packs"], dexamfetamine["pack_size"]) == (100, 1, 100)
    carboplatin = client.get("/pbs/drugs/" + client.get("/pbs/drugs", params={"q": "carboplatin"}).json()["drugs"][0]["item_code"]).json()
    assert all(i["restriction_level"] == "unrestricted" and i["listings"] == [] for i in carboplatin["items"])
    assert client.get("/pbs/drugs/99999Z").status_code == 404


def test_the_schedule_says_as_of_when_and_from_where(sign_in: SignIn, refresh: Refresh) -> None:
    client, _ = sign_in("trial_coordinator")
    empty = client.get("/pbs/schedule").json()
    assert (empty["schedule_date"], empty["current"], empty["last_refresh"]) == (None, None, None)

    refresh()
    status = client.get("/pbs/schedule").json()
    assert (status["schedule_date"], status["is_sample"], status["item_count"]) == ("2026-09-01", False, 23)
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
    assert client.get("/pbs/drugs", params={"q": "pembrolizumab"}).json()["drugs"][0]["item_count"] == 14


def test_the_sample_schedule_is_the_whole_schedule_marked_as_sample_data(sign_in: SignIn, refresh: Refresh) -> None:
    refresh(down=("*",))
    client, _ = sign_in("clinician")
    status = client.get("/pbs/schedule").json()
    assert status["is_sample"] is True
    assert (status["current"]["status"], status["current"]["source"], status["schedule_date"]) == ("partial", "sample", "2026-09-01")
    assert client.get("/pbs/drugs").json()["total"] > 500
    [pembrolizumab] = client.get("/pbs/drugs", params={"q": "pembrolizumab"}).json()["drugs"]
    drug = client.get(f"/pbs/drugs/{pembrolizumab['item_code']}").json()
    assert all(item["listings"] for item in drug["items"])


def test_developer_admins_have_no_pbs_lookup(sign_in: SignIn, refresh: Refresh) -> None:
    refresh()
    client, _ = sign_in("developer_admin")
    for path in ("/pbs/schedule", "/pbs/filters", "/pbs/drugs", "/pbs/drugs?q=pembro", "/pbs/drugs/12120X"):
        assert client.get(path).status_code == 403, path
