"""Cancer Types (MeSH) and Cancer Diagnosis (#37, design doc §6.3–6.4, §15 Stage 4a).

A Condition that is a primary cancer is extended by the Oncology module into a Cancer Diagnosis, with its
Stage (at diagnosis) and Disease Extent. Only clinicians record or correct one; a Patient may have several.
With Oncology inactive, the module's tools are gone but its facts stay visible read-only (ADR 0004).
"""

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed

MESH = Path(__file__).resolve().parents[2] / "app" / "specialties" / "oncology" / "data" / "mesh_neoplasms.json"
BREAST = {
    "cancer_type": "breast", "histology": "Invasive ductal carcinoma", "primary_site": "Breast", "laterality": "left",
    "dx_date": "2024-03-01", "stage_system": "TNM", "stage": "IIA", "disease_extent": "localised", "cancer_status": "active",
}


def with_oncology(sign_in: SignIn, committed: Seed, job_title: str = "clinician", **user: Any) -> tuple[TestClient, dict[str, Any]]:
    client, ids = sign_in(job_title, **user)
    admin = committed.user(ids["practice"], job_title="developer_admin")
    committed.insert("practice_module", practice_id=ids["practice"], module_key="oncology", changed_by_user_id=admin)
    return client, ids


def new_patient(client: TestClient) -> str:
    response = client.post("/patients", json={"given_name": "Jane", "family_name": "Citizen", "mrn": str(uuid.uuid4().int % 10**7)})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def record(client: TestClient, patient: str, **diagnosis: Any) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/cancer-diagnoses", json=BREAST | diagnosis)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_cancer_types_are_keyed_to_mesh(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed, "trial_coordinator")
    types = {t["key"]: t for t in client.get("/cancer-types").json()}
    assert len(types) >= 25
    assert (types["breast"]["display_name"], types["breast"]["mesh_term"], types["breast"]["mesh_id"]) == ("Breast cancer", "Breast Neoplasms", "D001943")
    assert types["nsclc"]["mesh_id"] == "D002289" and types["ovarian"]["staging_systems"] == ["FIGO"]
    # The full MeSH Neoplasms list is stored, ready but not offered.
    full = json.loads(MESH.read_text())["descriptors"]
    assert len(full) > 500 and {"D001943", "D002289", "D009382"} <= {d["mesh_id"] for d in full}


def test_a_clinician_records_a_primary_cancer_as_a_condition_extended_by_oncology(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    diagnosis = record(client, patient)
    assert diagnosis["name"] == "Breast cancer"  # the Cancer Type's name unless another is given
    assert (diagnosis["cancer_type"]["key"], diagnosis["cancer_type"]["mesh_term"]) == ("breast", "Breast Neoplasms")
    assert (diagnosis["stage"], diagnosis["stage_system"], diagnosis["disease_extent"]) == ("IIA", "TNM", "localised")
    [condition] = client.get(f"/patients/{patient}/conditions").json()
    assert (condition["id"], condition["name"], condition["extended_by_module"]) == (diagnosis["condition_id"], "Breast cancer", "oncology")
    kinds = committed.conn.execute(
        "SELECT subject_table FROM verification WHERE subject_id IN (%s, %s) ORDER BY subject_table",
        [diagnosis["id"], diagnosis["condition_id"]],
    ).fetchall()
    assert [k[0] for k in kinds] == ["cancer_diagnosis", "condition"]


def test_a_patient_may_have_several_primaries(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    record(client, patient)
    record(client, patient, cancer_type="melanoma", name="Melanoma, right calf", dx_date="2026-02-10", stage="IB", histology=None)
    names = [d["name"] for d in client.get(f"/patients/{patient}/cancer-diagnoses").json()]
    assert names == ["Breast cancer", "Melanoma, right calf"]  # by diagnosis date


@pytest.mark.parametrize("job_title", ["trial_coordinator", "secretary"])
def test_only_clinicians_record_or_correct_a_cancer_diagnosis(sign_in: SignIn, committed: Seed, job_title: str) -> None:
    clinician, ids = with_oncology(sign_in, committed)
    patient = new_patient(clinician)
    diagnosis = record(clinician, patient)
    other, _ = sign_in(job_title, practice=ids["practice"])
    assert other.post(f"/patients/{patient}/cancer-diagnoses", json=BREAST).status_code == 403
    assert other.patch(f"/patients/{patient}/cancer-diagnoses/{diagnosis['id']}", json={"stage": "IIB", "reason": "x"}).status_code == 403
    assert [d["stage"] for d in other.get(f"/patients/{patient}/cancer-diagnoses").json()] == ["IIA"]  # they read it
    # Nor may they change the Condition behind it from the Core.
    path = f"/patients/{patient}/conditions/{diagnosis['condition_id']}"
    assert other.patch(path, json={"name": "x", "reason": "y"}).status_code == 403


def test_correcting_stage_needs_a_clinician_and_a_reason(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    diagnosis = record(client, patient)
    path = f"/patients/{patient}/cancer-diagnoses/{diagnosis['id']}"
    assert client.patch(path, json={"stage": "IIB"}).status_code == 422
    fixed = client.patch(path, json={"stage": "IIB", "disease_extent": "metastatic", "disease_extent_as_of": "2026-09-01", "reason": "Typo"})
    assert (fixed.json()["stage"], fixed.json()["disease_extent"]) == ("IIB", "metastatic")
    [(before, after, reason)] = committed.conn.execute(
        "SELECT before, after, reason FROM verification WHERE subject_table = 'cancer_diagnosis' AND subject_id = %s AND reason IS NOT NULL",
        [diagnosis["id"]],
    ).fetchall()
    assert before == {"stage": "IIA", "disease_extent": "localised", "disease_extent_as_of": None}
    assert (after["stage"], reason) == ("IIB", "Typo")
    # A clinician can't correct the Condition behind it from the Core either: it's changed here.
    assert client.patch(f"/patients/{patient}/conditions/{diagnosis['condition_id']}", json={"name": "x", "reason": "y"}).status_code == 403


def test_removing_a_cancer_diagnosis_removes_its_condition_too(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    diagnosis = record(client, patient)
    assert client.request("DELETE", f"/patients/{patient}/cancer-diagnoses/{diagnosis['id']}", json={"reason": "Wrong Patient"}).status_code == 204
    assert client.get(f"/patients/{patient}/cancer-diagnoses").json() == []
    assert client.get(f"/patients/{patient}/conditions").json() == []


def test_invalid_diagnoses_are_refused(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    for bad in ({"cancer_type": "not_a_type"}, {"disease_extent": "everywhere"}, {"cancer_status": "cured"}):
        assert client.post(f"/patients/{patient}/cancer-diagnoses", json=BREAST | bad).status_code == 422, bad


def test_with_oncology_inactive_its_tools_are_gone_but_the_facts_stay_visible(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    record(client, patient, disease_extent="metastatic")
    committed.conn.execute("UPDATE practice_module SET is_active = false WHERE practice_id = %s", [ids["practice"]])
    assert client.get(f"/patients/{patient}/cancer-diagnoses").status_code == 403
    assert client.post(f"/patients/{patient}/cancer-diagnoses", json=BREAST).status_code == 403
    [oncology] = client.get(f"/patients/{patient}/inactive-module-facts").json()
    assert oncology["facts"] == ["Breast cancer: Stage IIA (TNM) at diagnosis, 1 Mar 2024; metastatic"]


def test_developer_admins_are_refused(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed, "developer_admin")
    patient = committed.patient(ids["practice"])
    assert client.get(f"/patients/{patient}/cancer-diagnoses").status_code == 403
    assert client.post(f"/patients/{patient}/cancer-diagnoses", json=BREAST).status_code == 403
