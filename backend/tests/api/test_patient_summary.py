"""The Patient Summary (#47, design doc §5 screen 15, §15 Stage 5): the consultation page, built from the Clinical
Record. Every section is present (an empty one says "None recorded" on screen), and each says when it was last
updated, by whom and in what Job Title: the Verification of its newest value.
"""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.core.clock import practice_today
from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, record, with_oncology
from tests.api.test_imaging import scan
from tests.api.test_treatment_courses import course
from tests.db.seed import Seed


def summary(client: TestClient, patient: str) -> dict[str, Any]:
    response = client.get(f"/patients/{patient}/summary")
    assert response.status_code == 200, response.text
    found: dict[str, Any] = response.json()
    return found


def test_an_empty_record_has_every_section_and_nothing_updated(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    found = summary(client, patient)
    assert set(found) == {"results", "treatment", "notes", "management", "history", "open_items"}
    assert found["history"] == {"comorbidities": [], "medications": [], "updated": None}
    assert found["results"]["updated"] is None


def test_the_summary_of_a_recorded_patient(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    client.post(f"/patients/{patient}/conditions", json={"name": "Type 2 diabetes"})
    today = practice_today()
    old = course(client, patient, breast["condition_id"], {"modality": "systemic", "intent": "adjuvant", "regimen_name": "AC-T",
                                                           "start_date": "2024-04-01", "end_date": "2024-09-30"})
    current = course(client, patient, breast["condition_id"], {"modality": "systemic", "intent": "palliative", "regimen_name": "Paclitaxel",
                                                               "start_date": str(today - timedelta(days=60))})
    client.post(f"/patients/{patient}/lab-panels", json={"collected_on": str(today - timedelta(days=30)), "panel": "FBC",
                                                         "results": [{"analyte": "Haemoglobin", "value": "98", "unit": "g/L", "ref_low": "115", "ref_high": "165"}]})
    scan(client, patient)
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    coordinator.post(f"/patients/{patient}/lab-panels", json={"collected_on": str(today), "panel": "FBC",
                                                              "results": [{"analyte": "Haemoglobin", "value": "105", "unit": "g/L", "ref_low": "115", "ref_high": "165"}]})
    client.post(f"/patients/{patient}/management-plans", json={"plan_text": "Continue paclitaxel.\nRestage in 3 months."})
    client.post(f"/patients/{patient}/clinical-notes", json={"note_type": "letter_to_referrer", "content": "Dear Dr Grey"})
    client.post(f"/patients/{patient}/clinical-notes", json={"note_type": "clinical_note", "content": "Tolerating well"})
    client.post(f"/patients/{patient}/medications", json={"drug_name": "Ondansetron", "category": "supportive_care"})
    stopped = client.post(f"/patients/{patient}/medications", json={"drug_name": "Dexamethasone"}).json()
    client.post(f"/patients/{patient}/medications/{stopped['id']}/stop", json={"end_date": str(today), "reason": "Finished"})

    found = summary(client, patient)
    results = found["results"]
    [haemoglobin] = results["latest_labs"]
    assert (haemoglobin["value"], haemoglobin["flag"]) == ("105", "low")
    assert [p["value"] for p in results["lab_trends"]["Haemoglobin"]] == ["98", "105"]
    assert results["updated"]["job_title"] == "trial_coordinator"  # the newest value's Verification
    assert [s["modality"] for s in results["scans"]] == ["CT"]
    assert [c["id"] for c in found["treatment"]["courses"]] == [current["id"]]  # the last 6 months only
    assert old["id"] not in {c["id"] for c in found["treatment"]["courses"]}
    assert found["management"]["plan"]["plan_text"] == "Continue paclitaxel.\nRestage in 3 months."
    assert (found["notes"]["latest_note"]["content"], found["notes"]["latest_letter"]["content"]) == ("Tolerating well", "Dear Dr Grey")
    assert [c["name"] for c in found["history"]["comorbidities"]] == ["Type 2 diabetes"]  # a cancer is in Diagnosis, not here
    assert [m["drug_name"] for m in found["history"]["medications"]] == ["Ondansetron"]  # current only
    assert found["history"]["updated"]["by"]


def test_the_developer_admin_never_sees_a_summary(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in()
    patient = new_patient(client)
    admin, _ = sign_in("developer_admin", practice=ids["practice"])
    assert admin.get(f"/patients/{patient}/summary").status_code == 403


def test_oncology_says_when_the_diagnosis_was_last_updated(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    assert client.get(f"/patients/{patient}/diagnosis-updated").json() is None
    breast = record(client, patient)
    client.post(f"/patients/{patient}/cancer-diagnoses/{breast['id']}/biomarkers", json={"name": "HER2", "result": "positive", "method": "IHC"})
    updated = client.get(f"/patients/{patient}/diagnosis-updated").json()
    assert (updated["job_title"], updated["subject_table"]) == ("clinician", "biomarker")
