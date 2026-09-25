"""Sites (#25): where a Practice sees Patients. Clinicians and developer admins manage them (§6.4 Change Settings)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed

ROOMS = {"name": "Harbourside rooms", "address": "1 Example St, Sydney NSW 2000", "lat": -33.8688, "lng": 151.2093}
CLINIC = {"name": "Example Hospital clinic", "address": "2 Example Rd, Sydney NSW 2000", "lat": -33.8898, "lng": 151.1873}


def add(client: TestClient, site: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/sites", json=site)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def verifications(committed: Seed, practice: Any) -> list[tuple[Any, ...]]:
    return committed.conn.execute(
        "SELECT action, before, after, reason FROM verification WHERE practice_id = %s AND subject_table = 'site'"
        " ORDER BY created_at, id",
        [practice],
    ).fetchall()


@pytest.mark.parametrize("job_title", ["clinician", "developer_admin"])
def test_clinicians_and_developer_admins_add_sites(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    site = add(client, ROOMS)
    assert site | {"id": None} == ROOMS | {"id": None, "is_primary": True}
    assert [s["name"] for s in client.get("/sites").json()] == ["Harbourside rooms"]


@pytest.mark.parametrize("job_title", ["trial_coordinator", "secretary"])
def test_others_see_sites_but_cant_change_them(sign_in: SignIn, committed: Seed, job_title: str) -> None:
    client, ids = sign_in(job_title)
    site = committed.site(ids["practice"], name="Harbourside rooms", is_primary=True)
    assert [s["name"] for s in client.get("/sites").json()] == ["Harbourside rooms"]
    assert client.post("/sites", json=CLINIC).status_code == 403
    assert client.patch(f"/sites/{site}", json={"name": "Renamed"}).status_code == 403
    assert client.request("DELETE", f"/sites/{site}", json={"reason": "Closed"}).status_code == 403


def test_the_first_site_is_primary_and_later_ones_are_not(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    assert add(client, ROOMS)["is_primary"] is True
    assert add(client, CLINIC)["is_primary"] is False


def test_choosing_another_primary_moves_it(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    rooms, clinic = add(client, ROOMS), add(client, CLINIC)
    changed = client.patch(f"/sites/{clinic['id']}", json={"is_primary": True})
    assert changed.status_code == 200 and changed.json()["is_primary"] is True
    primary = {s["id"]: s["is_primary"] for s in client.get("/sites").json()}
    assert primary == {rooms["id"]: False, clinic["id"]: True}


def test_the_primary_is_chosen_not_unset(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    rooms = add(client, ROOMS)
    assert client.patch(f"/sites/{rooms['id']}", json={"is_primary": False}).status_code == 422


def test_every_change_is_a_verification(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    rooms, clinic = add(client, ROOMS), add(client, CLINIC)
    client.patch(f"/sites/{clinic['id']}", json={"name": "Example Hospital outpatients"})
    client.request("DELETE", f"/sites/{clinic['id']}", json={"reason": "Clinic closed"})

    rows = verifications(committed, ids["practice"])
    assert rows[0] == ("edit", None, ROOMS | {"is_primary": True}, None)
    assert rows[2] == ("edit", {"name": CLINIC["name"]}, {"name": "Example Hospital outpatients"}, None)
    assert rows[3][0] == "delete" and rows[3][3] == "Clinic closed"
    assert rooms["id"] in {s["id"] for s in client.get("/sites").json()}


def test_deleting_needs_a_reason_and_hides_the_site(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    add(client, ROOMS)
    clinic = add(client, CLINIC)
    assert client.request("DELETE", f"/sites/{clinic['id']}", json={"reason": " "}).status_code == 422
    assert client.request("DELETE", f"/sites/{clinic['id']}", json={"reason": "Clinic closed"}).status_code == 204
    assert [s["name"] for s in client.get("/sites").json()] == [ROOMS["name"]]
    assert client.patch(f"/sites/{clinic['id']}", json={"name": "Back"}).status_code == 404


def test_the_primary_site_cant_be_deleted(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    rooms = add(client, ROOMS)
    refused = client.request("DELETE", f"/sites/{rooms['id']}", json={"reason": "Moving"})
    assert refused.status_code == 409
    assert "primary" in refused.json()["detail"]


def test_one_practice_cant_see_or_change_anothers_sites(sign_in: SignIn) -> None:
    ours, _ = sign_in("clinician")
    theirs, _ = sign_in("clinician")
    site = add(theirs, ROOMS)
    assert ours.get("/sites").json() == []
    assert ours.patch(f"/sites/{site['id']}", json={"name": "Ours now"}).status_code == 404
    assert ours.request("DELETE", f"/sites/{site['id']}", json={"reason": "x"}).status_code == 404


@pytest.mark.parametrize("bad", [{"name": " "}, {"name": "x", "lat": 91}, {"name": "x", "lng": -181}])
def test_invalid_sites_are_refused(sign_in: SignIn, bad: dict[str, Any]) -> None:
    client, _ = sign_in("clinician")
    assert client.post("/sites", json=bad).status_code == 422
