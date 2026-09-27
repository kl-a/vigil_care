"""Response Assessments and each course's best response (#43, design doc §6.3–6.4, §15 Stage 4c).

A Response Assessment says which way a Cancer Diagnosis is going (responding, stable or progressing), as a
radiology report or a clinician states it, optionally from an Imaging Study. With several primaries it may be
recorded "not sure which" (unattributed); only a clinician attributes or overrides one later. A Treatment
Course's **best response** is derived: the best direction among its Cancer Diagnosis's assessments dated during
the course, linked to the assessment it came from. It is never stored.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, record, with_oncology
from tests.api.test_imaging import CT, scan
from tests.api.test_treatment_courses import course
from tests.db.seed import Seed

PACLITAXEL = {"modality": "systemic", "intent": "palliative", "regimen_name": "Paclitaxel", "start_date": "2026-05-12"}


def assess(client: TestClient, patient: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/response-assessments", json={"source": "radiology_report"} | body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def best(client: TestClient, patient: str) -> dict[str, dict[str, Any]]:
    response = client.get(f"/patients/{patient}/best-responses")
    assert response.status_code == 200, response.text
    return {b["treatment_course_id"]: b for b in response.json()}


def test_a_ct_and_its_response_assessment_give_the_running_course_its_best_response(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    paclitaxel = course(client, patient, breast["condition_id"], PACLITAXEL)
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    ct = scan(coordinator, patient)
    stable = assess(coordinator, patient, {"cancer_diagnosis_id": breast["id"], "assessed_on": "2026-06-20", "direction": "stable"})
    responding = assess(coordinator, patient, {
        "cancer_diagnosis_id": breast["id"], "assessed_on": "2026-08-14", "direction": "responding", "imaging_study_id": ct["id"],
    })
    assert (responding["cancer_diagnosis_name"], responding["imaging_study_id"], responding["overridden_by_id"]) == ("Breast cancer", ct["id"], None)
    assess(coordinator, patient, {"cancer_diagnosis_id": breast["id"], "assessed_on": "2026-04-01", "direction": "responding"})  # before the course
    found = best(client, patient)[paclitaxel["id"]]
    assert (found["direction"], found["response_assessment_id"], found["imaging_study_id"]) == ("responding", responding["id"], ct["id"])
    assert found["explanation"] == "Responding: best response during Paclitaxel, on CT of 14 Aug 2026"
    listed = client.get(f"/patients/{patient}/response-assessments").json()
    assert [a["id"] for a in listed][:2] == [responding["id"], stable["id"]]  # newest first


def test_progression_during_a_course_is_its_best_response_only_if_nothing_better(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    ended = course(client, patient, breast["condition_id"], PACLITAXEL | {"end_date": "2026-07-01", "reason_stopped": "Progression"})
    assess(client, patient, {"cancer_diagnosis_id": breast["id"], "assessed_on": "2026-06-30", "direction": "progressing"})
    assess(client, patient, {"cancer_diagnosis_id": breast["id"], "assessed_on": "2026-08-01", "direction": "responding"})  # after it ended
    assert best(client, patient)[ended["id"]]["direction"] == "progressing"


def test_not_sure_which_cancer_diagnosis_then_a_clinician_attributes_it(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    record(client, patient, cancer_type="melanoma", name="Melanoma, right calf", dx_date="2026-02-10")
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    unsure = assess(coordinator, patient, {"cancer_diagnosis_id": None, "assessed_on": "2026-08-14", "direction": "progressing"})
    assert (unsure["cancer_diagnosis_id"], unsure["cancer_diagnosis_name"]) == (None, None)
    path = f"/patients/{patient}/response-assessments/{unsure['id']}/attribute"
    assert coordinator.post(path, json={"cancer_diagnosis_id": breast["id"]}).status_code == 403
    attributed = client.post(path, json={"cancer_diagnosis_id": breast["id"]})
    assert attributed.status_code == 200, attributed.text
    assert attributed.json()["cancer_diagnosis_name"] == "Breast cancer"
    assert client.post(path, json={"cancer_diagnosis_id": breast["id"]}).status_code == 409  # already attributed


def test_attributing_an_overridden_one_attributes_its_override_too(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    paclitaxel = course(client, patient, breast["condition_id"], PACLITAXEL)
    unsure = assess(client, patient, {"cancer_diagnosis_id": None, "assessed_on": "2026-08-14", "direction": "progressing"})
    override = client.post(f"/patients/{patient}/response-assessments/{unsure['id']}/override", json={"direction": "stable", "reason": "Flare"}).json()
    client.post(f"/patients/{patient}/response-assessments/{unsure['id']}/attribute", json={"cancer_diagnosis_id": breast["id"]})
    listed = {a["id"]: a for a in client.get(f"/patients/{patient}/response-assessments").json()}
    assert listed[override["id"]]["cancer_diagnosis_id"] == breast["id"]
    assert best(client, patient)[paclitaxel["id"]]["response_assessment_id"] == override["id"]


def test_only_a_clinician_overrides_and_the_override_counts_instead(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    paclitaxel = course(client, patient, breast["condition_id"], PACLITAXEL)
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    reported = assess(coordinator, patient, {"cancer_diagnosis_id": breast["id"], "assessed_on": "2026-08-14", "direction": "responding"})
    # A trial coordinator records what a report states, never a clinician's own assessment.
    assert coordinator.post(f"/patients/{patient}/response-assessments", json={
        "cancer_diagnosis_id": breast["id"], "assessed_on": "2026-08-14", "direction": "stable", "source": "clinician",
    }).status_code == 403
    path = f"/patients/{patient}/response-assessments/{reported['id']}/override"
    assert coordinator.post(path, json={"direction": "stable", "reason": "Pseudo-response"}).status_code == 403
    assert client.post(path, json={"direction": "stable"}).status_code == 422  # needs why
    override = client.post(path, json={"direction": "stable", "reason": "Pseudo-response on immunotherapy"}).json()
    assert (override["source"], override["overrides_id"], override["direction"], override["assessed_on"]) == (
        "clinician", reported["id"], "stable", "2026-08-14",
    )
    listed = {a["id"]: a for a in client.get(f"/patients/{patient}/response-assessments").json()}
    assert listed[reported["id"]]["overridden_by_id"] == override["id"]
    assert best(client, patient)[paclitaxel["id"]]["response_assessment_id"] == override["id"]
    assert client.post(path, json={"direction": "progressing", "reason": "again"}).status_code == 409  # already overridden


def test_an_assessment_is_of_the_patients_own_diagnosis_and_scan(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient, other = new_patient(client), new_patient(client)
    theirs = record(client, other)
    their_scan = scan(client, other, CT)
    body = {"assessed_on": "2026-08-14", "direction": "stable", "source": "radiology_report"}
    assert client.post(f"/patients/{patient}/response-assessments", json=body | {"cancer_diagnosis_id": theirs["id"]}).status_code == 404
    assert client.post(f"/patients/{patient}/response-assessments", json=body | {"imaging_study_id": their_scan["id"]}).status_code == 422


def test_best_response_is_no_longer_stored(committed: Seed) -> None:
    found = committed.conn.execute(
        "SELECT count(*) FROM information_schema.columns WHERE table_name = 'oncology_course_detail' AND column_name = 'best_response'"
    ).fetchone()
    assert found == (0,)


def test_they_stay_visible_read_only_when_oncology_is_off(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    course(client, patient, breast["condition_id"], PACLITAXEL)
    ct = scan(client, patient)
    assess(client, patient, {"cancer_diagnosis_id": breast["id"], "assessed_on": "2026-08-14", "direction": "responding", "imaging_study_id": ct["id"]})
    assess(client, patient, {"cancer_diagnosis_id": None, "assessed_on": "2026-09-01", "direction": "progressing"})
    committed.conn.execute("UPDATE practice_module SET is_active = false WHERE practice_id = (SELECT practice_id FROM patient WHERE id = %s)", [patient])
    assert client.get(f"/patients/{patient}/response-assessments").status_code == 403
    [oncology] = client.get(f"/patients/{patient}/inactive-module-facts").json()
    assert "Breast cancer: responding (radiology report, CT of 14 Aug 2026), 14 Aug 2026" in oncology["facts"]
    assert "Cancer Diagnosis not yet attributed: progressing (radiology report), 1 Sep 2026" in oncology["facts"]
    assert "Responding: best response during Paclitaxel, on CT of 14 Aug 2026" in oncology["facts"]
