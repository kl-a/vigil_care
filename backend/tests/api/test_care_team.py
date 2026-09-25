"""Care Team (#9): which Providers are involved in each Patient's care, in what role, from when to when."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed


def setup(client: TestClient, committed: Seed, practice: Any) -> dict[str, str]:
    patient = client.post("/patients", json={"given_name": "Jane", "family_name": "Citizen", "mrn": str(uuid.uuid4().int % 10**7)})
    assert patient.status_code == 201, patient.text
    oncologist = committed.provider(practice, title="Dr", first_name="Alex", last_name="Rivera", is_internal=True)
    gp = committed.provider(practice, title="Dr", first_name="Morgan", last_name="Grey", specialty="general_practice")
    return {"patient": patient.json()["id"], "oncologist": str(oncologist), "gp": str(gp)}


def add(client: TestClient, patient: str, **member: Any) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/care-team", json=member)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary"])
def test_staff_add_providers_to_a_patients_care_team(sign_in: SignIn, committed: Seed, job_title: str) -> None:
    client, ids = sign_in(job_title)
    s = setup(client, committed, ids["practice"])
    added = add(client, s["patient"], provider_id=s["oncologist"], role="treating_oncologist", is_primary=True,
                start_date="2024-03-01", notes="Leads treatment")
    assert added | {"id": None} == {
        "id": None, "provider_id": s["oncologist"], "provider_name": "Dr Alex Rivera", "role": "treating_oncologist",
        "is_primary": True, "start_date": "2024-03-01", "end_date": None, "notes": "Leads treatment", "is_current": True,
    }
    add(client, s["patient"], provider_id=s["gp"], role="referring_gp")
    team = client.get(f"/patients/{s['patient']}/care-team").json()
    assert [(m["provider_name"], m["role"], m["is_primary"]) for m in team] == [
        ("Dr Alex Rivera", "treating_oncologist", True),
        ("Dr Morgan Grey", "referring_gp", False),
    ]


def test_choosing_another_primary_moves_it(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("secretary")
    s = setup(client, committed, ids["practice"])
    first = add(client, s["patient"], provider_id=s["oncologist"], role="treating_oncologist", is_primary=True)
    second = add(client, s["patient"], provider_id=s["gp"], role="referring_gp", is_primary=True)
    assert second["is_primary"] is True
    team = {m["id"]: m["is_primary"] for m in client.get(f"/patients/{s['patient']}/care-team").json()}
    assert team == {first["id"]: False, second["id"]: True}


def test_ending_a_membership_makes_it_past(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    s = setup(client, committed, ids["practice"])
    gp = add(client, s["patient"], provider_id=s["gp"], role="referring_gp", start_date="2020-01-01")
    ended = client.patch(f"/patients/{s['patient']}/care-team/{gp['id']}", json={"end_date": "2024-06-30"})
    assert ended.status_code == 200
    assert (ended.json()["end_date"], ended.json()["is_current"]) == ("2024-06-30", False)
    assert client.patch(f"/patients/{s['patient']}/care-team/{gp['id']}", json={"end_date": "2019-01-01"}).status_code == 422


def test_adding_changing_and_ending_are_verifications(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    s = setup(client, committed, ids["practice"])
    gp = add(client, s["patient"], provider_id=s["gp"], role="referring_gp")
    client.patch(f"/patients/{s['patient']}/care-team/{gp['id']}", json={"role": "referring_specialist", "notes": "Now a specialist"})
    client.patch(f"/patients/{s['patient']}/care-team/{gp['id']}", json={"end_date": "2026-01-31"})
    rows = committed.conn.execute(
        "SELECT action, before, after FROM verification WHERE subject_table = 'care_team_member' AND subject_id = %s ORDER BY created_at, id",
        [gp["id"]],
    ).fetchall()
    assert [r[0] for r in rows] == ["edit", "edit", "edit"]
    assert rows[0][1] is None and rows[0][2]["role"] == "referring_gp"
    assert rows[1][1:] == ({"role": "referring_gp", "notes": None}, {"role": "referring_specialist", "notes": "Now a specialist"})
    assert rows[2][1:] == ({"end_date": None}, {"end_date": "2026-01-31"})


def test_only_this_practices_live_providers_join_a_care_team(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    s = setup(client, committed, ids["practice"])
    elsewhere = committed.provider(committed.practice())
    refused = client.post(f"/patients/{s['patient']}/care-team", json={"provider_id": str(elsewhere), "role": "surgeon"})
    assert refused.status_code == 422
    assert refused.json()["detail"] == "No such Provider in this Practice."
    client.request("DELETE", f"/providers/{s['gp']}", json={"reason": "Retired"})
    assert client.post(f"/patients/{s['patient']}/care-team", json={"provider_id": s["gp"], "role": "referring_gp"}).status_code == 422


def test_invalid_members_are_refused(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    s = setup(client, committed, ids["practice"])
    bad = [
        {"provider_id": s["gp"], "role": "astrologer"},
        {"provider_id": s["gp"], "role": "referring_gp", "start_date": "2025-01-01", "end_date": "2024-01-01"},
    ]
    for member in bad:
        assert client.post(f"/patients/{s['patient']}/care-team", json=member).status_code == 422


def test_a_providers_page_lists_the_patients_they_are_involved_with(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("trial_coordinator")
    s = setup(client, committed, ids["practice"])
    add(client, s["patient"], provider_id=s["oncologist"], role="treating_oncologist", is_primary=True)
    patients = client.get(f"/providers/{s['oncologist']}/patients").json()
    assert [(p["patient_id"], p["patient_name"], p["role"], p["is_current"]) for p in patients] == [
        (s["patient"], "Jane Citizen", "treating_oncologist", True)
    ]
    assert client.get(f"/providers/{s['gp']}/patients").json() == []


def test_removed_patients_leave_the_providers_list(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    s = setup(client, committed, ids["practice"])
    add(client, s["patient"], provider_id=s["gp"], role="referring_gp")
    client.request("DELETE", f"/patients/{s['patient']}", json={"reason": "Duplicate record"})
    assert client.get(f"/providers/{s['gp']}/patients").json() == []
    assert client.get(f"/patients/{s['patient']}/care-team").status_code == 404


def test_developer_admins_are_refused_every_care_team_endpoint(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    patient, provider = committed.patient(ids["practice"]), committed.provider(ids["practice"])
    member = committed.insert("care_team_member", practice_id=ids["practice"], patient_id=patient, provider_id=provider, role="surgeon")
    for method, path, body in [
        ("GET", f"/patients/{patient}/care-team", None),
        ("POST", f"/patients/{patient}/care-team", {"provider_id": str(provider), "role": "surgeon"}),
        ("PATCH", f"/patients/{patient}/care-team/{member}", {"notes": "x"}),
        ("GET", f"/providers/{provider}/patients", None),
    ]:
        assert client.request(method, path, json=body).status_code == 403, f"{method} {path}"


def test_another_practice_cant_see_or_change_our_care_teams(sign_in: SignIn, committed: Seed) -> None:
    ours, ids = sign_in("clinician")
    theirs, _ = sign_in("clinician")
    s = setup(ours, committed, ids["practice"])
    gp = add(ours, s["patient"], provider_id=s["gp"], role="referring_gp")
    assert theirs.get(f"/patients/{s['patient']}/care-team").status_code == 404
    assert theirs.patch(f"/patients/{s['patient']}/care-team/{gp['id']}", json={"notes": "x"}).status_code == 404
    assert theirs.get(f"/providers/{s['gp']}/patients").status_code == 404
