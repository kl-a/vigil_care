"""Entering the Clinical Record by hand, and Conditions (#35, design doc §6.2–6.4, §15 Stage 4).

Every add, edit and removal is a Verification; a correction needs a reason, given once per save. Who may enter
what comes from Verification Rights: clinicians and trial coordinators enter Conditions, secretaries only read
them, developer admins never see them. A Specialty Module's facts stay visible read-only when it's inactive
(ADR 0004, amended).
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed


def new_patient(client: TestClient) -> str:
    response = client.post("/patients", json={"given_name": "Jane", "family_name": "Citizen", "mrn": str(uuid.uuid4().int % 10**7)})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def add(client: TestClient, patient: str, **condition: Any) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/conditions", json=condition)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def verifications(committed: Seed, condition_id: str) -> list[tuple[Any, ...]]:
    return committed.conn.execute(
        "SELECT action, job_title_at_time, before, after, reason FROM verification"
        " WHERE subject_table = 'condition' AND subject_id = %s ORDER BY created_at, id",
        [condition_id],
    ).fetchall()


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator"])
def test_clinical_staff_add_conditions_entered_by_them(sign_in: SignIn, committed: Seed, job_title: str) -> None:
    client, ids = sign_in(job_title, display_name="Sam Lee (synthetic)")
    patient = new_patient(client)
    diabetes = add(client, patient, name="Type 2 diabetes", onset_date="2015-06-01", notes="Diet controlled")
    add(client, patient, name="COPD", status="resolved")
    assert diabetes | {"id": None, "entered": None} == {
        "id": None, "name": "Type 2 diabetes", "status": "active", "onset_date": "2015-06-01", "notes": "Diet controlled",
        "extended_by_module": None, "entered": None,
    }
    assert diabetes["entered"] | {"at": None} == {"by": "Sam Lee (synthetic)", "job_title": job_title, "at": None}
    listed = client.get(f"/patients/{patient}/conditions").json()
    assert [(c["name"], c["status"]) for c in listed] == [("Type 2 diabetes", "active"), ("COPD", "resolved")]

    row = committed.conn.execute("SELECT entered_by_user_id, source_fact_id FROM condition WHERE id = %s", [diabetes["id"]]).fetchone()
    assert row == (ids["user"], None)  # entered directly: provenance says who
    [(action, title, before, after, reason)] = verifications(committed, diabetes["id"])
    assert (action, title, before, reason) == ("edit", job_title, None, None)
    assert after == {"name": "Type 2 diabetes", "status": "active", "onset_date": "2015-06-01", "notes": "Diet controlled"}


def test_a_correction_needs_a_reason_given_once_per_save(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    condition = add(client, patient, name="Type 2 diabets")
    path = f"/patients/{patient}/conditions/{condition['id']}"
    assert client.patch(path, json={"name": "Type 2 diabetes"}).status_code == 422  # no reason
    assert client.patch(path, json={"name": "Type 2 diabetes", "reason": "  "}).status_code == 422
    saved = client.patch(path, json={"name": "Type 2 diabetes", "status": "resolved", "reason": "Typo; now resolved"})
    assert saved.status_code == 200
    assert (saved.json()["name"], saved.json()["status"]) == ("Type 2 diabetes", "resolved")
    edits = verifications(committed, condition["id"])
    assert len(edits) == 2  # one when added, one for the whole save
    assert edits[1][2:] == (
        {"name": "Type 2 diabets", "status": "active"}, {"name": "Type 2 diabetes", "status": "resolved"}, "Typo; now resolved",
    )
    # Saving without a change records nothing.
    client.patch(path, json={"name": "Type 2 diabetes", "reason": "No change"})
    assert len(verifications(committed, condition["id"])) == 2


def test_removing_a_condition_needs_a_reason_and_keeps_it_in_the_trail(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("trial_coordinator")
    patient = new_patient(client)
    condition = add(client, patient, name="Asthma")
    path = f"/patients/{patient}/conditions/{condition['id']}"
    assert client.request("DELETE", path, json={"reason": ""}).status_code == 422
    assert client.request("DELETE", path, json={"reason": "Wrong Patient"}).status_code == 204
    assert client.get(f"/patients/{patient}/conditions").json() == []
    assert verifications(committed, condition["id"])[-1][0::4] == ("delete", "Wrong Patient")
    assert client.patch(path, json={"name": "x", "reason": "y"}).status_code == 404


def test_secretaries_read_conditions_but_cant_change_them(sign_in: SignIn, committed: Seed) -> None:
    clinician, ids = sign_in("clinician")
    patient = new_patient(clinician)
    condition = add(clinician, patient, name="Hypertension")
    secretary, _ = sign_in("secretary", practice=ids["practice"])
    assert [c["name"] for c in secretary.get(f"/patients/{patient}/conditions").json()] == ["Hypertension"]
    path = f"/patients/{patient}/conditions/{condition['id']}"
    for method, url, body in [
        ("POST", f"/patients/{patient}/conditions", {"name": "Gout"}),
        ("PATCH", path, {"name": "HTN", "reason": "Shorter"}),
        ("DELETE", path, {"reason": "Not needed"}),
    ]:
        assert secretary.request(method, url, json=body).status_code == 403, f"{method} {url}"


def test_what_each_job_title_may_enter(sign_in: SignIn) -> None:
    rights = {title: sign_in(title)[0].get("/clinical/entry-rights").json() for title in ("clinician", "trial_coordinator", "secretary")}
    assert rights["clinician"]["condition"] is True
    assert rights["trial_coordinator"]["condition"] is True
    assert rights["secretary"]["condition"] is False
    assert all(value is False for value in rights["secretary"].values())


def test_developer_admins_are_refused_every_clinical_record_endpoint(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    patient = committed.patient(ids["practice"])
    condition = committed.insert("condition", practice_id=ids["practice"], patient_id=patient, name="Asthma", entered_by_user_id=ids["user"])
    for method, path, body in [
        ("GET", f"/patients/{patient}/conditions", None),
        ("POST", f"/patients/{patient}/conditions", {"name": "Gout"}),
        ("PATCH", f"/patients/{patient}/conditions/{condition}", {"name": "x", "reason": "y"}),
        ("DELETE", f"/patients/{patient}/conditions/{condition}", {"reason": "y"}),
        ("GET", f"/patients/{patient}/inactive-module-facts", None),
        ("GET", "/clinical/entry-rights", None),
    ]:
        assert client.request(method, path, json=body).status_code == 403, f"{method} {path}"


def test_another_practice_cant_see_or_change_our_conditions(sign_in: SignIn, committed: Seed) -> None:
    ours, _ = sign_in("clinician")
    theirs, _ = sign_in("clinician")
    patient = new_patient(ours)
    condition = add(ours, patient, name="Asthma")
    assert theirs.get(f"/patients/{patient}/conditions").status_code == 404
    assert theirs.patch(f"/patients/{patient}/conditions/{condition['id']}", json={"name": "x", "reason": "y"}).status_code == 404


def test_invalid_conditions_are_refused(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    for bad in ({"name": ""}, {"name": "Asthma", "status": "cured"}, {"name": "Asthma", "onset_date": "not a date"}):
        assert client.post(f"/patients/{patient}/conditions", json=bad).status_code == 422, bad


def test_an_inactive_modules_facts_stay_visible_read_only(sign_in: SignIn, committed: Seed) -> None:
    """ADR 0004 (amended): switching a module off removes its tools, never the clinician's view of its facts."""
    client, ids = sign_in("trial_coordinator")
    patient = new_patient(client)
    condition = committed.insert(
        "condition", practice_id=ids["practice"], patient_id=uuid.UUID(patient), name="Breast cancer",
        extended_by_module="oncology", entered_by_user_id=ids["user"],
    )
    breast = committed.conn.execute("SELECT id FROM cancer_type WHERE key = 'breast'").fetchone()
    cancer_type = breast[0] if breast else committed.insert("cancer_type", key="breast", display_name="Breast")
    committed.insert(
        "cancer_diagnosis", practice_id=ids["practice"], condition_id=condition, cancer_type_id=cancer_type,
        dx_date="2024-03-01", stage_system="TNM", stage="IIA", disease_extent="metastatic", entered_by_user_id=ids["user"],
    )
    # Oncology isn't active for this Practice: its facts still show, in its plain read-only form.
    [oncology] = client.get(f"/patients/{patient}/inactive-module-facts").json()
    assert (oncology["module"], oncology["display_name"]) == ("oncology", "Oncology")
    assert oncology["facts"] == ["Breast cancer: Stage IIA (TNM) at diagnosis, 1 Mar 2024; metastatic"]
    assert [c["extended_by_module"] for c in client.get(f"/patients/{patient}/conditions").json()] == ["oncology"]

    committed.insert("practice_module", practice_id=ids["practice"], module_key="oncology", changed_by_user_id=ids["user"])
    assert client.get(f"/patients/{patient}/inactive-module-facts").json() == []  # active: its own tabs show them
