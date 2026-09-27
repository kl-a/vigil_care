"""Recurrences (#39, design doc §6.3–6.4, §15 Stage 4a): a Suspected Recurrence of a Cancer Diagnosis, recorded
by a clinician or trial coordinator, stays suspected until a clinician resolves it: confirmed, a new primary
instead (the Cancer Diagnosis form prefilled from it), or ruled out with a reason.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import BREAST, new_patient, record, with_oncology
from tests.db.seed import Seed

LIVER = {"detected_on": "2026-02-10", "extent": "distant", "sites": ["liver"]}


def suspect(client: TestClient, patient: str, diagnosis: str, body: dict[str, Any] = LIVER) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/cancer-diagnoses/{diagnosis}/recurrences", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def setup(sign_in: SignIn, committed: Seed) -> tuple[TestClient, TestClient, str, str]:
    clinician, ids = with_oncology(sign_in, committed)
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    patient = new_patient(clinician)
    return clinician, coordinator, patient, record(clinician, patient)["id"]


def test_a_trial_coordinator_records_a_suspected_recurrence(sign_in: SignIn, committed: Seed) -> None:
    clinician, coordinator, patient, breast = setup(sign_in, committed)
    recurrence = suspect(coordinator, patient, breast)
    assert (recurrence["status"], recurrence["sites"], recurrence["extent"], recurrence["resolved"]) == ("suspected", ["liver"], "distant", None)
    assert recurrence["cancer_diagnosis_name"] == "Breast cancer"
    assert [r["id"] for r in clinician.get(f"/patients/{patient}/recurrences").json()] == [recurrence["id"]]


def test_only_a_clinician_confirms_it(sign_in: SignIn, committed: Seed) -> None:
    clinician, coordinator, patient, breast = setup(sign_in, committed)
    recurrence = suspect(coordinator, patient, breast)
    confirm = f"/patients/{patient}/recurrences/{recurrence['id']}/confirm"
    assert coordinator.post(confirm).status_code == 403
    confirmed = clinician.post(confirm).json()
    assert confirmed["status"] == "confirmed" and confirmed["resolved"]["by"]
    assert clinician.post(confirm).status_code == 409  # only a suspected one is resolved


def test_a_new_primary_instead_records_the_cancer_diagnosis_and_links_them(sign_in: SignIn, committed: Seed) -> None:
    clinician, coordinator, patient, breast = setup(sign_in, committed)
    recurrence = suspect(coordinator, patient, breast)
    path = f"/patients/{patient}/recurrences/{recurrence['id']}/new-primary"
    new_primary = BREAST | {"cancer_type": "hepatocellular", "name": "Hepatocellular carcinoma", "dx_date": "2026-02-10", "stage": None}
    assert coordinator.post(path, json=new_primary).status_code == 403
    resolved = clinician.post(path, json=new_primary).json()
    assert resolved["status"] == "reclassified_as_new_primary" and resolved["new_cancer_diagnosis_id"]
    names = [d["name"] for d in clinician.get(f"/patients/{patient}/cancer-diagnoses").json()]
    assert names == ["Breast cancer", "Hepatocellular carcinoma"]


def test_ruling_it_out_needs_a_reason(sign_in: SignIn, committed: Seed) -> None:
    clinician, coordinator, patient, breast = setup(sign_in, committed)
    recurrence = suspect(coordinator, patient, breast)
    path = f"/patients/{patient}/recurrences/{recurrence['id']}/rule-out"
    assert clinician.post(path, json={"reason": ""}).status_code == 422
    ruled_out = clinician.post(path, json={"reason": "Biopsy benign"}).json()
    assert (ruled_out["status"], ruled_out["ruled_out_reason"]) == ("ruled_out", "Biopsy benign")
    [(action, reason)] = committed.conn.execute(
        "SELECT action, reason FROM verification WHERE subject_table = 'recurrence' AND subject_id = %s AND reason IS NOT NULL",
        [recurrence["id"]],
    ).fetchall()
    assert (action, reason) == ("reject", "Biopsy benign")


@pytest.mark.parametrize("bad", [{"extent": "everywhere"}, {"detected_on": "soon"}])
def test_invalid_recurrences_are_refused(sign_in: SignIn, committed: Seed, bad: dict[str, Any]) -> None:
    clinician, _, patient, breast = setup(sign_in, committed)
    assert clinician.post(f"/patients/{patient}/cancer-diagnoses/{breast}/recurrences", json=LIVER | bad).status_code == 422


def test_secretaries_read_but_cant_record(sign_in: SignIn, committed: Seed) -> None:
    clinician, _, patient, breast = setup(sign_in, committed)
    suspect(clinician, patient, breast)
    secretary, _ = sign_in("secretary", practice=committed.conn.execute("SELECT practice_id FROM patient WHERE id = %s", [patient]).fetchone()[0])  # type: ignore[index]
    assert secretary.post(f"/patients/{patient}/cancer-diagnoses/{breast}/recurrences", json=LIVER).status_code == 403
    assert len(secretary.get(f"/patients/{patient}/recurrences").json()) == 1


def test_recurrences_show_with_their_cancer_diagnosis_read_only_when_oncology_is_off(sign_in: SignIn, committed: Seed) -> None:
    clinician, _, patient, breast = setup(sign_in, committed)
    suspect(clinician, patient, breast)
    committed.conn.execute(
        "UPDATE practice_module SET is_active = false WHERE practice_id = (SELECT practice_id FROM patient WHERE id = %s)", [patient]
    )
    [oncology] = clinician.get(f"/patients/{patient}/inactive-module-facts").json()
    assert "Breast cancer: suspected recurrence (distant: liver), 10 Feb 2026" in oncology["facts"]
