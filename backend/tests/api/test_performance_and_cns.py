"""ECOG and CNS status (#44, design doc §6.3, §15 Stage 4c): Oncology values over time, entered by clinicians and
trial coordinators. The latest ECOG is the Patient's current one.
"""

from typing import Any

import pytest

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, with_oncology
from tests.db.seed import Seed


def test_ecog_over_time_the_latest_is_current(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed, "trial_coordinator")
    patient = new_patient(client)
    for body in ({"scale": "ECOG", "value": 1, "assessed_on": "2026-06-01"}, {"scale": "ECOG", "value": 2, "assessed_on": "2026-09-20"}):
        assert client.post(f"/patients/{patient}/performance-status", json=body).status_code == 201
    listed = client.get(f"/patients/{patient}/performance-status").json()
    assert [(p["value"], p["assessed_on"]) for p in listed] == [(2, "2026-09-20"), (1, "2026-06-01")]  # newest first
    assert listed[0]["entered"]["job_title"] == "trial_coordinator"


@pytest.mark.parametrize("bad", [{"scale": "ECOG", "value": 6}, {"scale": "KPS", "value": 75}, {"scale": "Zubrod", "value": 1}])
def test_values_outside_their_scale_are_refused(sign_in: SignIn, committed: Seed, bad: dict[str, Any]) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    assert client.post(f"/patients/{patient}/performance-status", json=bad | {"assessed_on": "2026-09-20"}).status_code == 422


def test_cns_status_recorded_and_corrected(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    cns = client.post(f"/patients/{patient}/cns-status", json={
        "assessed_on": "2026-09-20", "present": True, "lesion_count": 2, "locations": ["left frontal", "cerebellum"],
        "treated": True, "treatment_type": "SRS", "symptomatic": False, "on_steroids": False, "leptomeningeal": False,
    })
    assert cns.status_code == 201, cns.text
    row = cns.json()
    assert (row["present"], row["lesion_count"], row["locations"]) == (True, 2, ["left frontal", "cerebellum"])
    fixed = client.patch(f"/patients/{patient}/cns-status/{row['id']}", json={"lesion_count": 3, "reason": "Recounted on MRI"})
    assert fixed.json()["lesion_count"] == 3
    assert client.patch(f"/patients/{patient}/cns-status/{row['id']}", json={"lesion_count": 4}).status_code == 422


def test_secretaries_read_but_cant_enter(sign_in: SignIn, committed: Seed) -> None:
    clinician, ids = with_oncology(sign_in, committed)
    patient = new_patient(clinician)
    secretary, _ = sign_in("secretary", practice=ids["practice"])
    assert secretary.post(f"/patients/{patient}/performance-status", json={"scale": "ECOG", "value": 1, "assessed_on": "2026-09-20"}).status_code == 403
    assert secretary.post(f"/patients/{patient}/cns-status", json={"assessed_on": "2026-09-20", "present": False}).status_code == 403
    assert secretary.get(f"/patients/{patient}/performance-status").status_code == 200


def test_removing_needs_a_reason(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    ecog = client.post(f"/patients/{patient}/performance-status", json={"scale": "ECOG", "value": 1, "assessed_on": "2026-09-20"}).json()
    path = f"/patients/{patient}/performance-status/{ecog['id']}"
    assert client.request("DELETE", path, json={"reason": ""}).status_code == 422
    assert client.request("DELETE", path, json={"reason": "Wrong Patient"}).status_code == 204
    assert client.get(f"/patients/{patient}/performance-status").json() == []


def test_with_oncology_inactive_they_stay_visible_read_only(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    client.post(f"/patients/{patient}/performance-status", json={"scale": "ECOG", "value": 2, "assessed_on": "2026-09-20"})
    client.post(f"/patients/{patient}/cns-status", json={"assessed_on": "2026-09-20", "present": True, "lesion_count": 1})
    committed.conn.execute("UPDATE practice_module SET is_active = false WHERE practice_id = %s", [ids["practice"]])
    assert client.get(f"/patients/{patient}/performance-status").status_code == 403
    [oncology] = client.get(f"/patients/{patient}/inactive-module-facts").json()
    assert "ECOG 2 (20 Sep 2026)" in oncology["facts"]
    assert "CNS disease present: 1 lesion (20 Sep 2026)" in oncology["facts"]
