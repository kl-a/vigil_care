"""Plan and notes (#45, design doc §6.3, §15 Stage 4c): Clinical Notes and letters, the Management Plan quoted
verbatim, and Next Steps. Notes and plans are Clinical Record values (clinicians and trial coordinators); Next
Steps any staff member adds and marks done (§6.4 row 1). Every change is a Verification; corrections say why.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn
from tests.db.seed import Seed


def new_patient(client: TestClient) -> str:
    response = client.post("/patients", json={"given_name": "Jane", "family_name": "Citizen", "mrn": str(uuid.uuid4().int % 10**7)})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def post(client: TestClient, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=body)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def actions(committed: Seed, table: str, row_id: str) -> list[tuple[Any, ...]]:
    return committed.conn.execute(
        "SELECT action, before, after, reason FROM verification WHERE subject_table = %s AND subject_id = %s ORDER BY created_at, id",
        [table, row_id],
    ).fetchall()


# --- Management Plan ---------------------------------------------------------------------------------------


def test_the_management_plan_is_kept_verbatim_with_its_author_and_history(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    patient = new_patient(client)
    author = committed.provider(ids["practice"], title="Dr", first_name="Alex", last_name="Rivera")
    text = "Continue letrozole.  Re-stage with CT in 3 months;\nconsider trial if progression."
    first = post(client, f"/patients/{patient}/management-plans", {"plan_text": text, "plan_date": "2026-09-01", "authored_by_provider_id": str(author)})
    assert (first["plan_text"], first["author_name"], first["plan_date"]) == (text, "Dr Alex Rivera", "2026-09-01")
    post(client, f"/patients/{patient}/management-plans", {"plan_text": "Start palliative chemotherapy.", "plan_date": "2026-09-20"})
    plans = client.get(f"/patients/{patient}/management-plans").json()
    assert [p["plan_date"] for p in plans] == ["2026-09-20", "2026-09-01"]  # newest first; earlier ones kept
    assert actions(committed, "management_plan", first["id"])[0][0] == "edit"


def test_a_plan_from_another_practices_provider_is_refused(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("clinician")
    patient = new_patient(client)
    elsewhere = committed.provider(committed.practice())
    response = client.post(f"/patients/{patient}/management-plans", json={"plan_text": "Plan", "authored_by_provider_id": str(elsewhere)})
    assert response.status_code == 422
    assert response.json()["detail"] == "No such Provider in this Practice."


def test_correcting_a_plan_needs_a_reason(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("trial_coordinator")
    patient = new_patient(client)
    plan = post(client, f"/patients/{patient}/management-plans", {"plan_text": "Contine letrozole."})
    path = f"/patients/{patient}/management-plans/{plan['id']}"
    assert client.patch(path, json={"plan_text": "Continue letrozole."}).status_code == 422
    fixed = client.patch(path, json={"plan_text": "Continue letrozole.", "reason": "Typo copying the letter"})
    assert fixed.json()["plan_text"] == "Continue letrozole."
    assert actions(committed, "management_plan", plan["id"])[1][1:] == (
        {"plan_text": "Contine letrozole."}, {"plan_text": "Continue letrozole."}, "Typo copying the letter",
    )


# --- Clinical Notes ------------------------------------------------------------------------------------------


def test_clinical_notes_and_letters_with_author_and_recipient(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    patient = new_patient(client)
    author = committed.provider(ids["practice"], title="Dr", first_name="Alex", last_name="Rivera")
    gp = committed.provider(ids["practice"], title="Dr", first_name="Morgan", last_name="Grey", specialty="general_practice")
    letter = post(client, f"/patients/{patient}/clinical-notes", {
        "note_type": "letter_to_referrer", "note_date": "2026-09-01", "author_provider_id": str(author),
        "recipient_provider_id": str(gp), "content": "Thank you for referring Jane.",
    })
    assert (letter["author_name"], letter["recipient_name"], letter["content"]) == ("Dr Alex Rivera", "Dr Morgan Grey", "Thank you for referring Jane.")
    post(client, f"/patients/{patient}/clinical-notes", {"note_type": "clinical_note", "note_date": "2026-09-10", "content": "Reviewed in clinic."})
    notes = client.get(f"/patients/{patient}/clinical-notes").json()
    assert [n["note_type"] for n in notes] == ["clinical_note", "letter_to_referrer"]  # newest first
    removed = client.request("DELETE", f"/patients/{patient}/clinical-notes/{letter['id']}", json={"reason": "Wrong Patient"})
    assert removed.status_code == 204
    assert len(client.get(f"/patients/{patient}/clinical-notes").json()) == 1


# --- Next Steps ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary"])
def test_staff_add_next_steps_and_mark_them_done(sign_in: SignIn, committed: Seed, job_title: str) -> None:
    client, _ = sign_in(job_title, display_name="Jordan Park (synthetic)")
    patient = new_patient(client)
    step = post(client, f"/patients/{patient}/next-steps", {"kind": "mdt", "description": "Discuss at breast MDT", "due_date": "2026-10-02"})
    assert (step["kind"], step["due_date"], step["done"]) == ("mdt", "2026-10-02", None)
    done = client.post(f"/patients/{patient}/next-steps/{step['id']}/done")
    assert done.status_code == 200
    assert done.json()["done"]["by"] == "Jordan Park (synthetic)"
    assert client.post(f"/patients/{patient}/next-steps/{step['id']}/done").status_code == 409  # already done
    assert [a[0] for a in actions(committed, "next_step", step["id"])] == ["edit", "edit"]


def test_next_steps_list_open_ones_first_by_due_date(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary")
    patient = new_patient(client)
    late = post(client, f"/patients/{patient}/next-steps", {"kind": "rescan", "description": "CT chest", "due_date": "2026-12-01"})
    soon = post(client, f"/patients/{patient}/next-steps", {"kind": "review", "description": "Clinic review", "due_date": "2026-10-01"})
    client.post(f"/patients/{patient}/next-steps/{soon['id']}/done")
    steps = client.get(f"/patients/{patient}/next-steps").json()
    assert [s["id"] for s in steps] == [late["id"], soon["id"]]


def test_correcting_or_removing_a_next_step_needs_a_reason(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary")
    patient = new_patient(client)
    step = post(client, f"/patients/{patient}/next-steps", {"kind": "rescan", "description": "CT chest", "due_date": "2026-12-01"})
    path = f"/patients/{patient}/next-steps/{step['id']}"
    assert client.patch(path, json={"due_date": "2026-12-08"}).status_code == 422
    assert client.patch(path, json={"due_date": "2026-12-08", "reason": "Rebooked"}).json()["due_date"] == "2026-12-08"
    assert client.request("DELETE", path, json={"reason": "Cancelled by oncologist"}).status_code == 204


# --- Who may do what ----------------------------------------------------------------------------------------


def test_secretaries_cant_write_notes_or_plans(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary")
    patient = new_patient(client)
    assert client.post(f"/patients/{patient}/management-plans", json={"plan_text": "Plan"}).status_code == 403
    assert client.post(f"/patients/{patient}/clinical-notes", json={"note_type": "clinical_note", "content": "x"}).status_code == 403
    assert client.get(f"/patients/{patient}/management-plans").status_code == 200  # but they read them


def test_developer_admins_are_refused_plan_and_notes(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    patient = committed.patient(ids["practice"])
    for method, path, body in [
        ("GET", f"/patients/{patient}/management-plans", None),
        ("POST", f"/patients/{patient}/management-plans", {"plan_text": "Plan"}),
        ("GET", f"/patients/{patient}/clinical-notes", None),
        ("GET", f"/patients/{patient}/next-steps", None),
        ("POST", f"/patients/{patient}/next-steps", {"kind": "review", "description": "x"}),
    ]:
        assert client.request(method, path, json=body).status_code == 403, f"{method} {path}"
