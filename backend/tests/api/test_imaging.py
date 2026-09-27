"""Imaging Studies and Findings (#43, design doc §6.3, §15 Stage 4c): the Core's record of a scan. The report's
impression is kept verbatim. Each Finding belongs to one study (never linked across studies) and is attributed to
a Condition only when the report says so.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient
from tests.db.seed import Seed

IMPRESSION = "Interval decrease in hepatic metastases.\n  No new lesions."
CT = {
    "modality": "CT", "body_region": "Chest, abdomen and pelvis", "study_date": "2026-08-14", "comparison_date": "2026-05-10",
    "impression": IMPRESSION,
    "findings": [
        {"site": "Liver segment VII", "description": "Metastasis", "size_mm": "18", "is_new": False, "is_measurable": True},
        {"site": "Lung", "laterality": "right", "description": "Nodule", "size_mm": "4", "is_new": True, "is_measurable": False},
    ],
}


def scan(client: TestClient, patient: str, body: dict[str, Any] = CT) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/imaging-studies", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def test_a_ct_with_two_findings_in_one_save(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("trial_coordinator")
    patient = new_patient(client)
    study = scan(client, patient)
    assert (study["modality"], study["impression"], study["comparison_date"]) == ("CT", IMPRESSION, "2026-05-10")  # verbatim
    assert [(f["site"], f["size_mm"], f["is_new"]) for f in study["findings"]] == [("Liver segment VII", "18", False), ("Lung", "4", True)]
    assert study["entered"]["job_title"] == "trial_coordinator"
    scan(client, patient, CT | {"study_date": "2026-05-10", "comparison_date": None, "findings": []})
    assert [s["study_date"] for s in client.get(f"/patients/{patient}/imaging-studies").json()] == ["2026-08-14", "2026-05-10"]


def test_a_finding_is_attributed_only_to_one_of_the_patients_conditions(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    mine = client.post(f"/patients/{patient}/conditions", json={"name": "Bowel cancer"}).json()["id"]
    theirs = client.post(f"/patients/{new_patient(client)}/conditions", json={"name": "Asthma"}).json()["id"]
    finding = {"description": "Liver lesion", "condition_id": mine}
    study = scan(client, patient, CT | {"findings": [finding]})
    assert (study["findings"][0]["condition_id"], study["findings"][0]["condition_name"]) == (mine, "Bowel cancer")
    assert client.post(f"/patients/{patient}/imaging-studies", json=CT | {"findings": [finding | {"condition_id": theirs}]}).status_code == 422
    assert client.post(f"/patients/{patient}/imaging-studies", json=CT | {"findings": [{"description": "x", "size_mm": "0"}]}).status_code == 422


def test_findings_are_added_corrected_and_removed_with_a_reason(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    study = scan(client, patient)
    base = f"/patients/{patient}/imaging-studies/{study['id']}"
    added = client.post(f"{base}/findings", json={"site": "Bone", "description": "Sclerotic lesion, T10"})
    assert added.status_code == 201, added.text
    finding = added.json()
    assert client.patch(f"{base}/findings/{finding['id']}", json={"size_mm": "9"}).status_code == 422
    assert client.patch(f"{base}/findings/{finding['id']}", json={"size_mm": "9", "reason": "Size in the addendum"}).json()["size_mm"] == "9"
    assert client.patch(base, json={"body_region": "Chest", "reason": "Typo"}).json()["body_region"] == "Chest"
    assert client.request("DELETE", f"{base}/findings/{finding['id']}", json={"reason": "Duplicate"}).status_code == 204
    assert len(client.get(f"/patients/{patient}/imaging-studies").json()[0]["findings"]) == 2


def test_removing_a_study_removes_its_findings(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in()
    patient = new_patient(client)
    study = scan(client, patient)
    assert client.request("DELETE", f"/patients/{patient}/imaging-studies/{study['id']}", json={"reason": "Wrong Patient"}).status_code == 204
    assert client.get(f"/patients/{patient}/imaging-studies").json() == []
    live = committed.conn.execute("SELECT count(*) FROM finding WHERE imaging_study_id = %s AND deleted_at IS NULL", [study["id"]]).fetchone()
    assert live == (0,)


def test_secretaries_read_but_cant_enter(sign_in: SignIn, committed: Seed) -> None:
    clinician, ids = sign_in()
    patient = new_patient(clinician)
    study = scan(clinician, patient)
    secretary, _ = sign_in("secretary", practice=ids["practice"])
    assert len(secretary.get(f"/patients/{patient}/imaging-studies").json()) == 1
    assert secretary.post(f"/patients/{patient}/imaging-studies", json=CT).status_code == 403
    assert secretary.post(f"/patients/{patient}/imaging-studies/{study['id']}/findings", json={"description": "x"}).status_code == 403
