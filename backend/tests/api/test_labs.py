"""Bloods and other labs (#42, design doc §15 Stage 4c): entered by hand as a panel, in one save with one
Verification; each value flagged H or L from the reference range the User typed (the report's own range).
"""

import uuid
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed

FBC = {
    "collected_on": "2026-09-20",
    "collected_time": "08:30",
    "panel": "FBC",
    "results": [
        {"analyte": "Haemoglobin", "value": "98", "unit": "g/L", "ref_low": "115", "ref_high": "165"},
        {"analyte": "Neutrophils", "value": "2.1", "unit": "x10^9/L", "ref_low": "2.0", "ref_high": "7.5"},
        {"analyte": "Platelets", "value": "480", "unit": "x10^9/L", "ref_low": "150", "ref_high": "400"},
        {"analyte": "Blood film", "value_text": "Normochromic", "unit": None},
        {"analyte": "CRP", "value": "12", "unit": "mg/L"},
    ],
}


def new_patient(client: TestClient) -> str:
    response = client.post("/patients", json={"given_name": "Jane", "family_name": "Citizen", "mrn": str(uuid.uuid4().int % 10**7)})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def add_panel(client: TestClient, patient: str, panel: dict[str, Any] = FBC) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/lab-panels", json=panel)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_a_panel_is_one_save_with_one_verification(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("trial_coordinator")
    patient = new_patient(client)
    panel = add_panel(client, patient)
    assert [r["analyte"] for r in panel["results"]] == ["Haemoglobin", "Neutrophils", "Platelets", "Blood film", "CRP"]
    assert {r["panel_id"] for r in panel["results"]} == {panel["panel_id"]}
    assert panel["results"][0]["collected_at"].startswith("2026-09-20T08:30:00")
    [(action, after)] = committed.conn.execute(
        "SELECT action, after FROM verification WHERE subject_table = 'lab_panel' AND subject_id = %s", [panel["panel_id"]]
    ).fetchall()
    assert action == "edit" and after["panel"] == "FBC" and len(after["results"]) == 5
    listed = client.get(f"/patients/{patient}/labs").json()
    assert len(listed) == 5 and all(r["entered"]["job_title"] == "trial_coordinator" for r in listed)


def test_flags_come_from_the_reference_range_typed(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    flags = {r["analyte"]: r["flag"] for r in add_panel(client, patient)["results"]}
    assert flags == {"Haemoglobin": "low", "Neutrophils": "normal", "Platelets": "high", "Blood film": None, "CRP": None}


def test_labs_list_newest_first_for_trends(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    add_panel(client, patient)
    add_panel(client, patient, {"collected_on": "2026-09-27", "panel": "FBC", "results": [
        {"analyte": "Haemoglobin", "value": "105", "unit": "g/L", "ref_low": "115", "ref_high": "165"},
    ]})
    haemoglobin = [(r["collected_at"][:10], r["value"]) for r in client.get(f"/patients/{patient}/labs").json() if r["analyte"] == "Haemoglobin"]
    assert haemoglobin == [("2026-09-27", "105"), ("2026-09-20", "98")]


def test_a_value_is_corrected_with_a_reason_and_reflagged(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    haemoglobin = add_panel(client, patient)["results"][0]
    path = f"/patients/{patient}/labs/{haemoglobin['id']}"
    assert client.patch(path, json={"value": "128"}).status_code == 422
    fixed = client.patch(path, json={"value": "128", "reason": "Misread the report"}).json()
    assert (fixed["value"], fixed["flag"]) == ("128", "normal")
    [(before, after, reason)] = committed.conn.execute(
        "SELECT before, after, reason FROM verification WHERE subject_table = 'lab_result' AND subject_id = %s", [haemoglobin["id"]]
    ).fetchall()
    assert (before, after, reason) == ({"value": "98"}, {"value": "128"}, "Misread the report")
    assert client.request("DELETE", path, json={"reason": "Duplicate"}).status_code == 204
    assert len(client.get(f"/patients/{patient}/labs").json()) == 4


def test_invalid_panels_are_refused(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    for bad in (
        {"collected_on": "2026-09-20", "results": []},
        {"collected_on": "2026-09-20", "results": [{"analyte": "Hb", "unit": "g/L"}]},  # no value
        {"collected_on": "2026-09-20", "results": [{"analyte": "Hb", "value": "high"}]},  # not a number
        {"results": [{"analyte": "Hb", "value": "98"}]},  # no date
        {"collected_on": "2026-09-20", "results": [{"analyte": "Hb", "value": "98", "ref_low": "165", "ref_high": "115"}]},
    ):
        assert client.post(f"/patients/{patient}/lab-panels", json=bad).status_code == 422, bad


def test_secretaries_and_developer_admins_cant_enter_labs(sign_in: SignIn, committed: Seed) -> None:
    secretary, _ = sign_in("secretary")
    patient = new_patient(secretary)
    assert secretary.post(f"/patients/{patient}/lab-panels", json=FBC).status_code == 403
    assert secretary.get(f"/patients/{patient}/labs").status_code == 200
    admin, ids = sign_in("developer_admin")
    theirs = committed.patient(ids["practice"])
    assert admin.get(f"/patients/{theirs}/labs").status_code == 403
