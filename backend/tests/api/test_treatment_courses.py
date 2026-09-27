"""Treatment Courses and Line of Therapy (#40, design doc §6.3, §15 Stage 4b).

A Treatment Course (Core) is given for one Condition: systemic (with its Regimen), surgery or radiation. With
Oncology active, a Cancer Diagnosis's palliative systemic courses get a derived Line of Therapy, numbered by
start date; a clinician may override one, with a reason, and later lines count on from it.
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.api.test_cancer_diagnoses import new_patient, record, with_oncology
from tests.db.seed import Seed

AC_T = {"modality": "systemic", "intent": "adjuvant", "regimen_name": "AC-T",
        "regimen_drugs": [{"drug": "Doxorubicin", "dose": "60 mg/m2"}, {"drug": "Cyclophosphamide", "dose": "600 mg/m2"}],
        "start_date": "2024-04-01", "end_date": "2024-09-30", "reason_stopped": "Completed"}


def course(client: TestClient, patient: str, condition: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/patients/{patient}/treatment-courses", json={"condition_id": condition} | body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def lines(client: TestClient, patient: str) -> dict[str, dict[str, Any]]:
    return {line["treatment_course_id"]: line for line in client.get(f"/patients/{patient}/lines-of-therapy").json()}


def breast_patient(sign_in: SignIn, committed: Seed, job_title: str = "clinician") -> tuple[TestClient, str, str]:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    condition = record(client, patient)["condition_id"]
    if job_title != "clinician":
        client, _ = sign_in(job_title, practice=ids["practice"])
    return client, patient, condition


def test_courses_of_each_modality_for_a_condition(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed, "trial_coordinator")
    course(client, patient, breast, {"modality": "surgery", "intent": "curative", "start_date": "2024-03-15",
                                     "details": {"procedure": "Left mastectomy", "margins": "Clear"}})
    adjuvant = course(client, patient, breast, AC_T)
    course(client, patient, breast, {"modality": "radiation", "intent": "adjuvant", "start_date": "2024-10-15",
                                     "details": {"site": "Left chest wall", "dose": "50 Gy", "fractions": "25"}})
    assert (adjuvant["condition_name"], adjuvant["regimen_name"], adjuvant["ongoing"]) == ("Breast cancer", "AC-T", False)
    assert [d["drug"] for d in adjuvant["regimen_drugs"]] == ["Doxorubicin", "Cyclophosphamide"]
    listed = client.get(f"/patients/{patient}/treatment-courses").json()
    assert [c["modality"] for c in listed] == ["radiation", "systemic", "surgery"]  # most recent start first


def test_a_regimen_belongs_to_systemic_courses_only(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    bad = client.post(f"/patients/{patient}/treatment-courses", json={"condition_id": breast, "modality": "surgery", "regimen_name": "AC-T"})
    assert bad.status_code == 422
    ends_first = client.post(f"/patients/{patient}/treatment-courses", json={"condition_id": breast} | AC_T | {"end_date": "2024-01-01"})
    assert ends_first.status_code == 422


def test_ending_a_course_is_a_correction_with_a_reason(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    ongoing = course(client, patient, breast, AC_T | {"end_date": None, "reason_stopped": None})
    assert ongoing["ongoing"] is True
    path = f"/patients/{patient}/treatment-courses/{ongoing['id']}"
    assert client.patch(path, json={"end_date": "2024-09-30"}).status_code == 422
    ended = client.patch(path, json={"end_date": "2024-09-30", "reason_stopped": "Completed", "reason": "Last cycle given"}).json()
    assert (ended["ongoing"], ended["reason_stopped"]) == (False, "Completed")


def test_line_of_therapy_is_derived_for_palliative_systemic_courses(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    adjuvant = course(client, patient, breast, AC_T)
    first = course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Paclitaxel",
                                             "start_date": "2025-03-12", "end_date": "2025-11-01"})
    derived = lines(client, patient)
    assert adjuvant["id"] not in derived  # adjuvant: no line
    assert (derived[first["id"]]["line"], derived[first["id"]]["overridden"]) == (1, False)
    assert derived[first["id"]]["explanation"] == "1st line: 1st palliative systemic course of Breast cancer, started 12 Mar 2025"
    second = course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Capecitabine",
                                              "start_date": "2025-11-20"})
    assert lines(client, patient)[second["id"]]["line"] == 2


def test_a_clinician_overrides_a_line_and_later_lines_count_on(sign_in: SignIn, committed: Seed) -> None:
    client, ids = with_oncology(sign_in, committed)
    patient = new_patient(client)
    breast = record(client, patient)["condition_id"]
    first = course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Paclitaxel", "start_date": "2025-03-12"})
    maintenance = course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Maintenance", "start_date": "2025-08-01"})
    third = course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Capecitabine", "start_date": "2025-11-20"})
    path = f"/patients/{patient}/treatment-courses/{maintenance['id']}/line-of-therapy"
    coordinator, _ = sign_in("trial_coordinator", practice=ids["practice"])
    assert coordinator.put(path, json={"line": 1, "reason": "Maintenance of 1st line"}).status_code == 403
    assert client.put(path, json={"line": 1}).status_code == 422  # needs a reason
    assert client.put(path, json={"line": 1, "reason": "Maintenance of 1st line"}).status_code == 200
    now = lines(client, patient)
    assert (now[first["id"]]["line"], now[maintenance["id"]]["line"], now[third["id"]]["line"]) == (1, 1, 2)
    assert now[maintenance["id"]]["overridden"] is True
    assert now[maintenance["id"]]["explanation"] == "1st line, set by a clinician: Maintenance of 1st line"
    # Clearing the override goes back to deriving it.
    assert client.put(path, json={"line": None, "reason": "Counted after all"}).status_code == 200
    assert lines(client, patient)[third["id"]]["line"] == 3


def test_an_override_only_on_a_palliative_systemic_course(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    adjuvant = course(client, patient, breast, AC_T)
    assert client.put(f"/patients/{patient}/treatment-courses/{adjuvant['id']}/line-of-therapy", json={"line": 1, "reason": "x"}).status_code == 422


def test_secretaries_read_but_cant_enter(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed, "secretary")
    assert client.post(f"/patients/{patient}/treatment-courses", json={"condition_id": breast} | AC_T).status_code == 403
    assert client.get(f"/patients/{patient}/treatment-courses").status_code == 200
    assert client.get(f"/patients/{patient}/lines-of-therapy").status_code == 200


def test_a_course_is_for_one_of_the_patients_own_conditions(sign_in: SignIn, committed: Seed) -> None:
    client, patient, _ = breast_patient(sign_in, committed)
    other = new_patient(client)
    theirs = client.post(f"/patients/{other}/conditions", json={"name": "Asthma"}).json()["id"]
    assert client.post(f"/patients/{patient}/treatment-courses", json={"condition_id": theirs} | AC_T).status_code == 422


def test_changing_the_intent_of_a_course_with_an_overridden_line_is_refused(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    palliative = course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Paclitaxel", "start_date": "2025-03-12"})
    client.put(f"/patients/{patient}/treatment-courses/{palliative['id']}/line-of-therapy", json={"line": 2, "reason": "Counted elsewhere"})
    refused = client.patch(f"/patients/{patient}/treatment-courses/{palliative['id']}", json={"intent": "adjuvant", "reason": "Wrong intent"})
    assert refused.status_code == 422
    assert client.get(f"/patients/{patient}/treatment-courses").json()[0]["intent"] == "palliative"  # nothing changed


def test_lines_of_therapy_stay_visible_read_only_when_oncology_is_off(sign_in: SignIn, committed: Seed) -> None:
    client, patient, breast = breast_patient(sign_in, committed)
    course(client, patient, breast, {"modality": "systemic", "intent": "palliative", "regimen_name": "Paclitaxel", "start_date": "2025-03-12"})
    committed.conn.execute("UPDATE practice_module SET is_active = false WHERE practice_id = (SELECT practice_id FROM patient WHERE id = %s)", [patient])
    [oncology] = client.get(f"/patients/{patient}/inactive-module-facts").json()
    assert "1st line: 1st palliative systemic course of Breast cancer, started 12 Mar 2025" in oncology["facts"]
