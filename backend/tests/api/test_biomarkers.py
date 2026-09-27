"""Biomarkers and Differing Biomarker Results (#38, design doc §6.3, §15 Stage 4a).

Every result is kept (never overwritten); the latest per Biomarker and variant is current. Results of the same
Biomarker and variant on one Cancer Diagnosis whose categories differ are flagged "Results differ", by a
deterministic rule with no interpretation. A clinician can move a result to a new primary.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, record, with_oncology
from tests.db.seed import Seed

HER2_PRIMARY = {"name": "HER2", "result": "positive", "value_num": "3", "value_unit": "IHC score", "method": "IHC",
                "specimen_site": "Left breast", "specimen_kind": "primary", "collected_on": "2024-03-01"}
HER2_LIVER = {"name": "HER2", "result": "negative", "value_num": "0", "value_unit": "IHC score", "method": "IHC",
              "specimen_site": "Liver", "specimen_kind": "metastasis", "collected_on": "2026-02-10"}


def add(client: TestClient, patient: str, diagnosis: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/cancer-diagnoses/{diagnosis}/biomarkers", json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def history(client: TestClient, patient: str, diagnosis: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = client.get(f"/patients/{patient}/cancer-diagnoses/{diagnosis}/biomarkers").json()
    return rows


def test_every_result_is_kept_and_the_latest_is_current(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed, "trial_coordinator")
    patient = new_patient(client)
    clinician, _ = sign_in("clinician", practice=_practice(committed, patient))
    breast = record(clinician, patient)["id"]
    add(client, patient, breast, {"name": "ER", "result": "positive", "value_num": "90", "value_unit": "%", "method": "IHC", "collected_on": "2024-03-01"})
    add(client, patient, breast, {"name": "ER", "result": "positive", "value_num": "70", "value_unit": "%", "method": "IHC", "collected_on": "2026-02-10"})
    rows = history(client, patient, breast)
    assert [(r["name"], r["value_num"], r["current"], r["differs"]) for r in rows] == [
        ("ER", "70", True, False), ("ER", "90", False, False),  # newest first; the same category: nothing differs
    ]


def test_differing_results_are_flagged_without_interpretation(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["id"]
    add(client, patient, breast, HER2_PRIMARY)
    add(client, patient, breast, HER2_LIVER)
    add(client, patient, breast, {"name": "EGFR", "variant": "exon 19 deletion", "result": "detected", "method": "NGS", "collected_on": "2024-03-01"})
    add(client, patient, breast, {"name": "EGFR", "variant": "T790M", "result": "detected", "method": "ctDNA", "collected_on": "2026-02-10"})
    rows = {(r["name"], r["variant"], r["collected_on"]): r for r in history(client, patient, breast)}
    assert rows[("HER2", None, "2026-02-10")]["differs"] is True and rows[("HER2", None, "2024-03-01")]["differs"] is True
    # A different variant is a different Biomarker result, not a differing one.
    assert rows[("EGFR", "T790M", "2026-02-10")]["differs"] is False
    # Category comparison ignores case and spacing, and nothing else.
    add(client, patient, breast, HER2_LIVER | {"result": " Negative ", "collected_on": "2026-03-01"})
    assert sum(1 for r in history(client, patient, breast) if r["differs"]) == 3


def test_a_result_is_never_overwritten_only_removed_and_re_entered(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["id"]
    wrong = add(client, patient, breast, HER2_PRIMARY | {"result": "negative"})
    path = f"/patients/{patient}/cancer-diagnoses/{breast}/biomarkers/{wrong['id']}"
    assert client.patch(path, json={"result": "positive", "reason": "x"}).status_code == 405
    assert client.request("DELETE", path, json={"reason": "Transcribed wrongly"}).status_code == 204
    add(client, patient, breast, HER2_PRIMARY)
    assert [r["result"] for r in history(client, patient, breast)] == ["positive"]


def test_a_clinician_moves_a_result_to_a_new_primary(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["id"]
    add(client, patient, breast, HER2_PRIMARY)
    liver = add(client, patient, breast, HER2_LIVER)
    second = record(client, patient, cancer_type="hepatocellular", name="Hepatocellular carcinoma", dx_date="2026-02-10")["id"]
    move = f"/patients/{patient}/cancer-diagnoses/{breast}/biomarkers/{liver['id']}/move"
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    assert coordinator.post(move, json={"cancer_diagnosis_id": second, "reason": "New primary"}).status_code == 403
    moved = client.post(move, json={"cancer_diagnosis_id": second, "reason": "Biopsy shows a new primary"})
    assert moved.status_code == 200, moved.text
    assert [r["specimen_site"] for r in history(client, patient, second)] == ["Liver"]
    assert all(not r["differs"] for r in history(client, patient, breast))
    [(action, reason)] = committed.conn.execute(
        "SELECT action, reason FROM verification WHERE subject_table = 'biomarker' AND subject_id = %s AND action = 'move'", [liver["id"]]
    ).fetchall()
    assert reason == "Biopsy shows a new primary"


def test_secretaries_read_but_cant_enter(sign_in: SignIn, committed: Seed) -> None:
    clinician, ids = with_oncology(sign_in, committed)
    patient = new_patient(clinician)
    breast = record(clinician, patient)["id"]
    secretary, _ = sign_in("secretary", practice=ids["practice"])
    assert secretary.post(f"/patients/{patient}/cancer-diagnoses/{breast}/biomarkers", json=HER2_PRIMARY).status_code == 403
    assert secretary.get(f"/patients/{patient}/cancer-diagnoses/{breast}/biomarkers").status_code == 200


def test_the_current_biomarkers_show_on_the_cancer_diagnosis(sign_in: SignIn, committed: Seed) -> None:
    client, _ = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["id"]
    add(client, patient, breast, HER2_PRIMARY)
    add(client, patient, breast, HER2_LIVER)
    [diagnosis] = client.get(f"/patients/{patient}/cancer-diagnoses").json()
    assert [(b["name"], b["result"], b["differs"]) for b in diagnosis["current_biomarkers"]] == [("HER2", "negative", True)]


def _practice(committed: Seed, patient: str) -> Any:
    return committed.conn.execute("SELECT practice_id FROM patient WHERE id = %s", [patient]).fetchone()[0]  # type: ignore[index]


def test_biomarkers_stay_visible_read_only_when_oncology_is_off(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["id"]
    add(client, patient, breast, HER2_PRIMARY)
    add(client, patient, breast, HER2_LIVER)
    committed.conn.execute("UPDATE practice_module SET is_active = false WHERE practice_id = %s", [ids["practice"]])
    [oncology] = client.get(f"/patients/{patient}/inactive-module-facts").json()
    assert "Breast cancer: HER2 negative (0 IHC score) (results differ)" in oncology["facts"]
