"""What the list screens show at a glance (#57): how many of each Clinical Record kind a Patient has (for the
Clinical Data sub-tabs), and, from Oncology, each Patient's Cancer Types and Disease Extent (for the Patient List)."""

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, record, with_oncology
from tests.api.test_imaging import scan
from tests.db.seed import Seed


def test_the_core_counts_each_clinical_data_sub_tab(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    client.post(f"/patients/{patient}/conditions", json={"name": "Asthma"})
    client.post(f"/patients/{patient}/lab-panels", json={"collected_on": "2026-09-01", "results": [
        {"analyte": "Haemoglobin", "value": "120"}, {"analyte": "Platelets", "value": "200"}]})
    client.post(f"/patients/{patient}/lab-panels", json={"collected_on": "2026-09-08", "results": [{"analyte": "Haemoglobin", "value": "118"}]})
    scan(client, patient)
    client.post(f"/patients/{patient}/management-plans", json={"plan_text": "Plan"})
    counts = client.get(f"/patients/{patient}/clinical-counts").json()
    # Labs count tests (analytes), not results.
    assert counts == {"conditions": 1, "labs": 2, "imaging": 1, "treatment": 0, "plan": 1}


def test_oncology_counts_its_sub_tabs(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)
    client.post(f"/patients/{patient}/cancer-diagnoses/{breast['id']}/biomarkers", json={"name": "HER2", "result": "positive"})
    client.post(f"/patients/{patient}/performance-status", json={"value": 1, "assessed_on": "2026-09-01"})
    counts = client.get(f"/patients/{patient}/oncology-counts").json()
    assert counts == {"cancer-diagnosis": 1, "response-assessments": 0, "biomarkers": 1, "performance-status": 1, "cns": 0}


def test_oncology_gives_the_patient_list_each_patients_cancer_types_and_disease_extent(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    record(client, patient)  # breast, localised
    record(client, patient, cancer_type="melanoma", name="Melanoma", disease_extent="metastatic")
    other = new_patient(client)
    rows = {r["patient_id"]: r for r in client.get("/patient-list/oncology").json()}
    assert rows[patient]["values"] == {"cancer_types": ["Breast cancer", "Melanoma"], "disease_extent": ["Metastatic"]}  # the most advanced
    assert other not in rows
    admin, ids = sign_in("developer_admin")
    assert admin.get("/patient-list/oncology").status_code == 403
