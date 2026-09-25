"""Per-Practice activation of Specialty Modules (#15): developer admins only, recorded, data kept."""

import pytest

from tests.api.conftest import SignIn
from tests.db.seed import Seed


def activate(committed: Seed, ids: dict[str, object]) -> None:
    committed.insert("practice_module", practice_id=ids["practice"], module_key="oncology", changed_by_user_id=ids["user"])


def test_installed_modules_are_listed_with_their_state(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    modules = client.get("/modules").json()
    assert modules == [{"key": "oncology", "display_name": "Oncology", "version": "0.1.0", "is_active": False}]


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary"])
def test_only_developer_admins_switch_modules(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    assert client.patch("/modules/oncology", json={"is_active": True}).status_code == 403


def test_activating_and_deactivating_records_verifications(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    assert client.patch("/modules/oncology", json={"is_active": True}).json()["is_active"] is True
    assert client.patch("/modules/oncology", json={"is_active": False, "reason": "Not using it yet"}).json()["is_active"] is False
    rows = committed.conn.execute(
        "SELECT action, job_title_at_time, before, after, reason FROM verification"
        " WHERE practice_id = %s AND subject_table = 'practice_module' ORDER BY created_at",
        [ids["practice"]],
    ).fetchall()
    assert rows == [
        ("activate_module", "developer_admin", {"is_active": False}, {"is_active": True}, None),
        ("deactivate_module", "developer_admin", {"is_active": True}, {"is_active": False}, "Not using it yet"),
    ]


def test_switching_to_the_same_state_records_nothing(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    client.patch("/modules/oncology", json={"is_active": False})
    count = committed.conn.execute(
        "SELECT count(*) FROM verification WHERE practice_id = %s AND subject_table = 'practice_module'", [ids["practice"]]
    ).fetchone()
    assert count == (0,)


def test_an_unknown_module_is_404(sign_in: SignIn) -> None:
    client, _ = sign_in("developer_admin")
    assert client.patch("/modules/cardiology", json={"is_active": True}).status_code == 404


def test_the_active_configuration_follows_the_switch(sign_in: SignIn) -> None:
    admin, ids = sign_in("developer_admin")
    clinician, _ = sign_in("clinician", practice=ids["practice"])
    assert clinician.get("/modules/active").json() == {"active_modules": [], "sections": [], "patient_tabs": []}

    admin.patch("/modules/oncology", json={"is_active": True})
    active = clinician.get("/modules/active").json()
    assert active["active_modules"] == ["oncology"]
    assert {"module": "oncology", "segment": "treatment-options", "label": "Treatment Options"} in active["patient_tabs"]
    assert "cancer-diagnoses" in {s["id"] for s in active["sections"]}


def test_deactivating_keeps_the_modules_data(sign_in: SignIn, committed: Seed) -> None:
    admin, ids = sign_in("developer_admin")
    admin.patch("/modules/oncology", json={"is_active": True})
    clinician = committed.user(ids["practice"])
    everyone = {"practice": ids["practice"], "user": clinician, "patient": committed.patient(ids["practice"])}
    cancer_type = committed.insert("cancer_type", key="breast-test", display_name="Breast")
    diagnosis = committed.insert(
        "cancer_diagnosis", practice_id=ids["practice"], condition_id=committed.condition(everyone),
        cancer_type_id=cancer_type, entered_by_user_id=clinician,
    )
    admin.patch("/modules/oncology", json={"is_active": False, "reason": "Pause"})
    still_there = committed.conn.execute("SELECT count(*) FROM cancer_diagnosis WHERE id = %s", [diagnosis]).fetchone()
    assert still_there == (1,)


def test_another_practices_switch_doesnt_affect_ours(sign_in: SignIn) -> None:
    ours, _ = sign_in("developer_admin")
    theirs, _ = sign_in("developer_admin")
    theirs.patch("/modules/oncology", json={"is_active": True})
    assert ours.get("/modules/active").json()["active_modules"] == []
