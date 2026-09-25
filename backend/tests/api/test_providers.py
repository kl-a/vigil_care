"""Provider directory (#7): internal clinicians and external referrers, specialists and trial-site contacts."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed


def gp(**overrides: Any) -> dict[str, Any]:
    return {
        "title": "Dr",
        "first_name": "Morgan",
        "last_name": "Grey",
        "provider_number": f"{uuid.uuid4().int % 10**6:06d}AB",
        "specialty": "general_practice",
        "is_internal": False,
        "organisation": "Example Family Practice",
        "phone": "02 5550 0300",
        "email": "reception@example-family.example.com",
        "fax": "02 5550 0301",
        "notes": "Refers most of our lung patients.",
        **overrides,
    }


def add(client: TestClient, provider: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/providers", json=provider)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary"])
def test_staff_add_and_edit_providers(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    provider = add(client, gp())
    assert provider["display_name"] == "Dr Morgan Grey"
    assert provider | {"id": None, "display_name": None} == gp(provider_number=provider["provider_number"]) | {"id": None, "display_name": None}

    changed = client.patch(f"/providers/{provider['id']}", json={"phone": "02 5550 0399", "notes": ""})
    assert changed.status_code == 200
    assert (changed.json()["phone"], changed.json()["notes"]) == ("02 5550 0399", None)


def test_developer_admins_read_the_directory_but_dont_change_it(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    committed.provider(ids["practice"], last_name="Quinn")
    assert [p["last_name"] for p in client.get("/providers").json()] == ["Quinn"]
    assert client.post("/providers", json=gp()).status_code == 403


def test_the_list_is_searched_by_name_and_filtered(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary")
    add(client, gp())
    add(client, gp(first_name="Taylor", last_name="Quinn", specialty="surgery", organisation="Example Hospital"))
    add(client, gp(title=None, first_name="Alex", last_name="Rivera", specialty="medical_oncology", is_internal=True))

    names = lambda query: [p["last_name"] for p in client.get("/providers", params=query).json()]  # noqa: E731
    assert names({}) == ["Grey", "Quinn", "Rivera"]
    assert names({"q": "qui"}) == ["Quinn"]
    assert names({"q": "morgan grey"}) == ["Grey"]
    assert names({"specialty": "surgery"}) == ["Quinn"]
    assert names({"internal": "true"}) == ["Rivera"]
    assert names({"internal": "false"}) == ["Grey", "Quinn"]


def test_provider_numbers_are_unique_within_the_practice(sign_in: SignIn) -> None:
    ours, _ = sign_in("clinician")
    first = add(ours, gp())
    duplicate = ours.post("/providers", json=gp(first_name="Sam", provider_number=first["provider_number"]))
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == f"Provider number {first['provider_number']} is already used by Dr Morgan Grey."

    other = add(ours, gp(first_name="Sam", last_name="Other"))
    clash = ours.patch(f"/providers/{other['id']}", json={"provider_number": first["provider_number"]})
    assert clash.status_code == 409

    theirs, _ = sign_in("clinician")
    assert theirs.post("/providers", json=gp(provider_number=first["provider_number"])).status_code == 201


def test_every_change_is_a_verification(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    provider = add(client, gp())
    client.patch(f"/providers/{provider['id']}", json={"organisation": "Example Medical Centre"})
    rows = committed.conn.execute(
        "SELECT action, before, after FROM verification WHERE subject_table = 'provider' AND subject_id = %s ORDER BY created_at, id",
        [provider["id"]],
    ).fetchall()
    assert [r[0] for r in rows] == ["edit", "edit"]
    assert rows[0][1] is None and rows[0][2]["last_name"] == "Grey"
    assert rows[1][1:] == ({"organisation": "Example Family Practice"}, {"organisation": "Example Medical Centre"})


def test_soft_deleting_needs_a_reason_and_hides_the_provider(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("secretary")
    provider = add(client, gp())
    assert client.request("DELETE", f"/providers/{provider['id']}", json={"reason": ""}).status_code == 422
    assert client.request("DELETE", f"/providers/{provider['id']}", json={"reason": "Retired"}).status_code == 204

    assert client.get("/providers").json() == []
    assert client.get(f"/providers/{provider['id']}").status_code == 404
    row = committed.conn.execute(
        "SELECT action, reason FROM verification WHERE subject_table = 'provider' AND subject_id = %s AND action = 'delete'",
        [provider["id"]],
    ).fetchone()
    assert row == ("delete", "Retired")
    # The number stays taken, so a removed Provider's history can't be confused with a new one's.
    reused = client.post("/providers", json=gp(provider_number=provider["provider_number"]))
    assert reused.status_code == 409 and "removed Provider" in reused.json()["detail"]


def test_another_practices_providers_are_invisible(sign_in: SignIn) -> None:
    ours, _ = sign_in("clinician")
    theirs, _ = sign_in("clinician")
    provider = add(theirs, gp())
    assert ours.get("/providers").json() == []
    assert ours.get(f"/providers/{provider['id']}").status_code == 404
    assert ours.patch(f"/providers/{provider['id']}", json={"phone": "x"}).status_code == 404
    assert ours.request("DELETE", f"/providers/{provider['id']}", json={"reason": "x"}).status_code == 404


@pytest.mark.parametrize(
    "bad",
    [{"first_name": " "}, {"last_name": ""}, {"specialty": "astrology"}, {"email": "not-an-email"}],
)
def test_invalid_providers_are_refused(sign_in: SignIn, bad: dict[str, Any]) -> None:
    client, _ = sign_in("clinician")
    assert client.post("/providers", json=gp(**bad)).status_code == 422
