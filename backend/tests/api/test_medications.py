"""The Medication Manager (#41, design doc §5 screen 10, §6.3, §15 Stage 4b).

A Medication is picked from the drug reference (so it links to the PBS Drug Lookup) or entered as free text,
marked "not in the drug reference". A cancer drug's Medication links to its Treatment Course; stopping it changes
the Medication, never the course. Every change is in the Medication's change log with who and why, and verified.
Clinicians and trial coordinators enter them; secretaries read.
"""

import uuid
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient
from tests.api.test_treatment_courses import AC_T, breast_patient, course
from tests.db.seed import Seed


def drug(committed: Seed, generic: str, *, cancer: bool = False, items: tuple[str, ...] = ("1165H",)) -> tuple[uuid.UUID, str]:
    """A drug in the reference (Shared Reference Data), named uniquely so tests don't collide."""
    name = f"{generic} {uuid.uuid4().hex[:6]}"
    committed.conn.execute(
        "INSERT INTO drug_reference (generic_name, brand_names, is_cancer_drug, pbs_item_codes) VALUES (%s, '[\"Brand\"]', %s, %s::jsonb)",
        [name, cancer, str(list(items)).replace("'", '"')],
    )
    [[drug_id]] = committed.conn.execute("SELECT id FROM drug_reference WHERE generic_name = %s", [name]).fetchall()
    return drug_id, name


def add(client: TestClient, patient: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/medications", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def changes(client: TestClient, patient: str) -> list[dict[str, Any]]:
    response = client.get(f"/patients/{patient}/medication-changes")
    assert response.status_code == 200, response.text
    found: list[dict[str, Any]] = response.json()
    return found


def test_a_medication_from_the_drug_reference_links_to_the_pbs_lookup(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("trial_coordinator")
    patient = new_patient(client)
    prescriber = committed.provider(ids["practice"], title="Dr", first_name="Alex", last_name="Rivera")
    drug_id, name = drug(committed, "Dexamfetamine", items=("1165H", "1166J"))
    med = add(client, patient, {
        "drug_reference_id": str(drug_id), "dose_amount": "5", "dose_unit": "mg", "frequency": "twice_daily", "route": "oral",
        "indication": "Fatigue", "start_date": "2026-06-01", "prescribed_by_provider_id": str(prescriber),
    })
    assert (med["drug_name"], med["in_drug_reference"], med["pbs_item_codes"]) == (name, True, ["1165H", "1166J"])
    assert (med["status"], med["dose_display"], med["prescriber_name"]) == ("active", "5 mg", "Dr Alex Rivera")
    assert med["entered"]["job_title"] == "trial_coordinator"
    [log] = changes(client, patient)
    assert (log["change_type"], log["medication_id"], log["drug_name"], log["reason"]) == ("added", med["id"], name, None)
    assert log["by"]


def test_a_free_text_medication_says_it_isnt_in_the_drug_reference(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    med = add(client, patient, {"drug_name": "Turmeric capsules", "category": "supplement"})
    assert (med["drug_name"], med["in_drug_reference"], med["pbs_item_codes"]) == ("Turmeric capsules", False, [])
    assert client.post(f"/patients/{patient}/medications", json={}).status_code == 422  # a drug or a name


def test_a_change_needs_a_reason_and_is_logged_by_kind(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    drug_id, _ = drug(committed, "Ondansetron")
    med = add(client, patient, {"drug_reference_id": str(drug_id), "dose_amount": "8", "dose_unit": "mg", "frequency": "prn"})
    path = f"/patients/{patient}/medications/{med['id']}"
    assert client.patch(path, json={"dose_amount": "4"}).status_code == 422
    changed = client.patch(path, json={"dose_amount": "4", "reason": "Drowsy at 8 mg"}).json()
    assert changed["dose_display"] == "4 mg"
    client.patch(path, json={"indication": "Nausea", "reason": "Indication missed"})
    client.patch(path, json={"indication": "Nausea", "reason": "Nothing changes"})  # no change, nothing logged
    logs = changes(client, patient)
    assert [(log["change_type"], log["reason"]) for log in logs] == [
        ("corrected", "Indication missed"), ("dose_changed", "Drowsy at 8 mg"), ("added", None),
    ]
    assert (logs[1]["previous_value"], logs[1]["new_value"]) == ({"dose_amount": "8"}, {"dose_amount": "4"})
    verified = committed.conn.execute("SELECT count(*) FROM verification WHERE subject_table = 'medication' AND subject_id = %s", [med["id"]]).fetchone()
    assert verified == (3,)  # each change is verified as well as logged


def test_stopping_and_restarting_a_medication(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    med = add(client, patient, {"drug_name": "Dexamethasone", "start_date": "2026-05-01"})
    path = f"/patients/{patient}/medications/{med['id']}"
    assert client.post(f"{path}/stop", json={"end_date": "2026-06-01"}).status_code == 422  # needs why
    assert client.post(f"{path}/stop", json={"end_date": "2026-04-01", "reason": "x"}).status_code == 422  # before it started
    stopped = client.post(f"{path}/stop", json={"end_date": "2026-06-01", "reason": "Course of steroids finished"}).json()
    assert (stopped["status"], stopped["end_date"], stopped["reason_discontinued"]) == ("discontinued", "2026-06-01", "Course of steroids finished")
    assert client.post(f"{path}/stop", json={"end_date": "2026-06-02", "reason": "again"}).status_code == 409
    restarted = client.post(f"{path}/restart", json={"reason": "Headaches back"}).json()
    assert (restarted["status"], restarted["end_date"], restarted["reason_discontinued"]) == ("active", None, None)
    assert [log["change_type"] for log in changes(client, patient)] == ["restarted", "discontinued", "added"]


def test_stopping_one_drug_of_a_regimen_leaves_the_course_ongoing(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    ongoing = course(client, patient, breast, AC_T | {"end_date": None, "reason_stopped": None})
    drug_id, _ = drug(committed, "Doxorubicin", cancer=True)
    med = add(client, patient, {"drug_reference_id": str(drug_id), "category": "cancer_treatment", "treatment_course_id": ongoing["id"]})
    assert (med["is_cancer_drug"], med["treatment_course_id"], med["treatment_course_name"]) == (True, ongoing["id"], "AC-T")
    client.post(f"/patients/{patient}/medications/{med['id']}/stop", json={"end_date": "2024-06-01", "reason": "Cardiotoxicity"})
    [still] = client.get(f"/patients/{patient}/treatment-courses").json()
    assert still["ongoing"] is True


def test_a_medication_links_only_to_the_patients_own_course_and_providers(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    other = new_patient(client)
    theirs = client.post(f"/patients/{other}/conditions", json={"name": "Asthma"}).json()["id"]
    their_course = course(client, other, theirs, {"modality": "systemic", "regimen_name": "Omalizumab"})
    assert client.post(f"/patients/{patient}/medications", json={"drug_name": "X", "treatment_course_id": their_course["id"]}).status_code == 422
    elsewhere = committed.provider(committed.practice())
    assert client.post(f"/patients/{patient}/medications", json={"drug_name": "X", "prescribed_by_provider_id": str(elsewhere)}).status_code == 422


def test_secretaries_read_but_cant_add_change_or_stop(sign_in: SignIn, committed: Seed) -> None:
    clinician, ids = sign_in()
    patient = new_patient(clinician)
    med = add(clinician, patient, {"drug_name": "Paracetamol"})
    secretary, _ = sign_in("secretary", practice=ids["practice"])
    assert secretary.get(f"/patients/{patient}/medications").status_code == 200
    assert secretary.get(f"/patients/{patient}/medication-changes").status_code == 200
    assert secretary.post(f"/patients/{patient}/medications", json={"drug_name": "X"}).status_code == 403
    path = f"/patients/{patient}/medications/{med['id']}"
    assert secretary.patch(path, json={"notes": "x", "reason": "x"}).status_code == 403
    assert secretary.post(f"{path}/stop", json={"end_date": "2026-01-01", "reason": "x"}).status_code == 403
    assert secretary.request("DELETE", path, json={"reason": "x"}).status_code == 403


def test_removing_a_medication_entered_in_error(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    med = add(client, patient, {"drug_name": "Wrong patient's drug"})
    assert client.request("DELETE", f"/patients/{patient}/medications/{med['id']}", json={"reason": "Wrong Patient"}).status_code == 204
    assert client.get(f"/patients/{patient}/medications").json() == []
    removed = changes(client, patient)[0]
    assert (removed["change_type"], removed["new_value"], removed["reason"]) == ("corrected", None, "Wrong Patient")
