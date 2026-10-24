"""Open Items (#48, design doc §6.3, §15 Stage 5): derived, never stored, never dismissed. Each clears only by
acting on what's behind it. The Core raises Next Steps coming due; Oncology, while active, raises Differing
Biomarker Results, unattributed Response Assessments, new unattributed Findings and Suspected Recurrences.
"""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.core.clock import practice_today
from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, record, with_oncology
from tests.api.test_imaging import scan
from tests.db.seed import Seed


def items(client: TestClient, patient: str) -> list[dict[str, Any]]:
    response = client.get(f"/patients/{patient}/open-items")
    assert response.status_code == 200, response.text
    found: list[dict[str, Any]] = response.json()
    return found


def of_type(client: TestClient, patient: str, kind: str) -> list[dict[str, Any]]:
    return [item for item in items(client, patient) if item["type"] == kind]


def act(client: TestClient, item: dict[str, Any], label: str, **body: Any) -> None:
    action = next(a for a in item["actions"] if a["label"] == label)
    response = client.post(action["path"], json=body)
    assert response.status_code < 300, response.text


def biomarker(client: TestClient, patient: str, diagnosis: str, result: str, collected: str) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/cancer-diagnoses/{diagnosis}/biomarkers",
                           json={"name": "HER2", "result": result, "method": "IHC", "collected_on": collected})
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def test_a_next_step_is_an_open_item_from_seven_days_before_it_is_due_until_done(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in()
    patient = new_patient(client)
    today = practice_today()
    soon = client.post(f"/patients/{patient}/next-steps", json={"kind": "mdt", "description": "Breast MDT", "due_date": str(today + timedelta(days=7))}).json()
    client.post(f"/patients/{patient}/next-steps", json={"kind": "rescan", "description": "Restaging CT", "due_date": str(today + timedelta(days=8))})
    client.post(f"/patients/{patient}/next-steps", json={"kind": "review", "description": "Overdue review", "due_date": str(today - timedelta(days=2))})
    [overdue, due] = of_type(client, patient, "next_step")  # soonest first
    assert (due["title"], due["subject_id"], due["who"]) == ("Breast MDT", soon["id"], "staff")
    assert overdue["detail"].startswith("Overdue since")
    secretary, _ = sign_in("secretary", practice=ids["practice"])
    act(secretary, due, "Mark done")
    assert [i["title"] for i in of_type(client, patient, "next_step")] == ["Overdue review"]


def test_differing_biomarker_results_until_a_clinician_marks_them_seen_and_again_after_a_later_result(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["id"]
    biomarker(client, patient, breast, "positive", "2024-03-01")
    assert of_type(client, patient, "differing_biomarker_results") == []
    latest = biomarker(client, patient, breast, "negative", "2026-02-10")
    [item] = of_type(client, patient, "differing_biomarker_results")
    assert (item["title"], item["who"], item["subject_id"]) == ("HER2 results differ", "clinician", latest["id"])
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    seen = next(a for a in item["actions"] if a["label"] == "Seen")
    assert coordinator.post(seen["path"], json={}).status_code == 403
    # Another kind of `accept` on the result (e.g. Extraction Review, Stage 9) isn't a "Seen".
    committed.insert("verification", practice_id=ids["practice"], subject_table="biomarker", subject_id=latest["id"], user_id=ids["user"],
                     job_title_at_time="clinician", action="accept")
    assert len(of_type(client, patient, "differing_biomarker_results")) == 1
    act(client, item, "Seen", note="Discussed at MDT")
    assert of_type(client, patient, "differing_biomarker_results") == []
    note = committed.conn.execute("SELECT reason FROM verification WHERE subject_id = %s AND after ? 'seen'", [latest["id"]]).fetchone()
    assert note == ("Discussed at MDT",)
    biomarker(client, patient, breast, "equivocal", "2026-06-01")  # a later differing result raises it again
    assert len(of_type(client, patient, "differing_biomarker_results")) == 1


def test_an_unattributed_response_assessment_until_a_clinician_attributes_it(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    client.post(f"/patients/{patient}/response-assessments",
                json={"assessed_on": "2026-09-01", "direction": "progressing", "source": "radiology_report"})
    [item] = of_type(client, patient, "unattributed_response_assessment")
    attribute = next(a for a in item["actions"] if a["label"] == "Attribute")
    assert (attribute["input"], attribute["field"], [c["name"] for c in attribute["choices"]]) == ("choose", "cancer_diagnosis_id", ["Breast cancer"])
    act(client, item, "Attribute", cancer_diagnosis_id=breast["id"])
    assert of_type(client, patient, "unattributed_response_assessment") == []


def test_a_new_unattributed_finding_in_a_patient_with_a_cancer_diagnosis(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    scan(client, patient)  # a new 4 mm lung nodule, not attributed
    assert of_type(client, patient, "unattributed_finding") == []  # no Cancer Diagnosis yet
    breast = record(client, patient)
    [item] = of_type(client, patient, "unattributed_finding")
    assert item["title"] == "New Finding not attributed: Nodule, Lung, right"
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    attribute = next(a for a in item["actions"] if a["label"] == "Attribute")
    assert coordinator.post(attribute["path"], json={"condition_id": breast["condition_id"]}).status_code == 403
    act(client, item, "Attribute", condition_id=breast["condition_id"])
    assert of_type(client, patient, "unattributed_finding") == []


def test_a_suspected_recurrence_until_a_clinician_resolves_it(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    client.post(f"/patients/{patient}/cancer-diagnoses/{breast['id']}/recurrences", json={"detected_on": "2026-02-10", "extent": "distant", "sites": ["liver"]})
    [item] = of_type(client, patient, "suspected_recurrence")
    assert (item["title"], item["who"]) == ("Suspected Recurrence of Breast cancer", "clinician")
    assert [a["label"] for a in item["actions"]] == ["Confirm", "Rule out"]
    rule_out = item["actions"][1]
    assert rule_out["input"] == "reason" and client.post(rule_out["path"], json={}).status_code == 422
    act(client, item, "Confirm")
    assert of_type(client, patient, "suspected_recurrence") == []


def test_oncology_raises_nothing_while_inactive(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    client.post(f"/patients/{patient}/cancer-diagnoses/{breast['id']}/recurrences", json={"extent": "distant"})
    committed.conn.execute("UPDATE practice_module SET is_active = false WHERE practice_id = (SELECT practice_id FROM patient WHERE id = %s)", [patient])
    assert items(client, patient) == []


def test_the_practice_wide_queue_filters_by_type_and_who_can_act_and_never_shows_another_practice(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    client.post(f"/patients/{patient}/cancer-diagnoses/{breast['id']}/recurrences", json={"extent": "distant"})
    client.post(f"/patients/{patient}/next-steps", json={"kind": "mdt", "description": "Breast MDT", "due_date": str(practice_today())})
    elsewhere, _ = sign_in()
    elsewhere_patient = new_patient(elsewhere)
    elsewhere.post(f"/patients/{elsewhere_patient}/next-steps", json={"kind": "mdt", "description": "Not ours", "due_date": str(practice_today())})
    queue = client.get("/open-items").json()
    assert sorted(i["type"] for i in queue) == ["next_step", "suspected_recurrence"]
    assert {i["patient_name"] for i in queue} == {"Jane Citizen"}
    assert [i["type"] for i in client.get("/open-items?type=next_step").json()] == ["next_step"]
    assert [i["type"] for i in client.get("/open-items?who=clinician").json()] == ["suspected_recurrence"]
    admin, _ = sign_in("developer_admin", practice=ids["practice"])
    assert admin.get("/open-items").status_code == 403
    assert admin.get(f"/patients/{patient}/open-items").status_code == 403

