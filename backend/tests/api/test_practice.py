"""Practice details (#14): everyone signed in sees them; clinicians and developer admins change them (§6.4)."""

import pytest

from tests.api.conftest import SignIn
from tests.db.seed import Seed

DETAILS = {
    "name": "Harbourside Oncology (synthetic)",
    "address": "1 Example St, Sydney NSW 2000",
    "phone": "02 9000 0000",
    "fax": "02 9000 0001",
    "email": "reception@harbourside.example",
    "abn": "51 824 753 556",
    "lat": -33.8688,
    "lng": 151.2093,
}


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary", "developer_admin"])
def test_everyone_signed_in_sees_their_practices_details(sign_in: SignIn, job_title: str) -> None:
    client, ids = sign_in(job_title)
    practice = client.get("/practice")
    assert practice.status_code == 200
    assert practice.json()["id"] == str(ids["practice"])
    assert practice.json()["name"] == "Synthetic Oncology Practice"


@pytest.mark.parametrize("job_title", ["clinician", "developer_admin"])
def test_clinicians_and_developer_admins_change_the_details(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    changed = client.patch("/practice", json=DETAILS)
    assert changed.status_code == 200
    assert changed.json() | {"id": None} == DETAILS | {"id": None}
    assert client.get("/practice").json()["lat"] == -33.8688


@pytest.mark.parametrize("job_title", ["trial_coordinator", "secretary"])
def test_others_cant_change_the_details(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    assert client.patch("/practice", json={"phone": "02 1111 1111"}).status_code == 403


def test_each_change_records_a_verification_with_only_what_changed(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    client.patch("/practice", json={"phone": "02 9000 0000", "name": "Synthetic Oncology Practice"})
    rows = committed.conn.execute(
        "SELECT action, subject_table, subject_id, job_title_at_time, before, after FROM verification"
        " WHERE practice_id = %s AND subject_table = 'practice'",
        [ids["practice"]],
    ).fetchall()
    assert rows == [("edit", "practice", ids["practice"], "clinician", {"phone": None}, {"phone": "02 9000 0000"})]


def test_an_unchanged_save_records_nothing(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    client.patch("/practice", json={"name": "Synthetic Oncology Practice"})
    count = committed.conn.execute(
        "SELECT count(*) FROM verification WHERE practice_id = %s AND subject_table = 'practice'", [ids["practice"]]
    ).fetchone()
    assert count == (0,)


def test_one_practice_cant_read_or_change_another(sign_in: SignIn, committed: Seed) -> None:
    ours, our_ids = sign_in("clinician")
    theirs, their_ids = sign_in("clinician")
    # Naming the other Practice doesn't help: the request is always about the signed-in User's own.
    changed = ours.patch("/practice", json={"id": str(their_ids["practice"]), "name": "Our Practice (synthetic)"})
    assert changed.json()["id"] == str(our_ids["practice"])
    assert theirs.get("/practice").json()["name"] == "Synthetic Oncology Practice"
    assert theirs.get("/practice").json()["id"] == str(their_ids["practice"])


@pytest.mark.parametrize(
    "bad",
    [{"name": " "}, {"lat": 91}, {"lng": -181}, {"abn": "12 345"}, {"email": "not-an-email"}],
)
def test_invalid_details_are_refused(sign_in: SignIn, bad: dict[str, object]) -> None:
    client, _ = sign_in("clinician")
    assert client.patch("/practice", json=bad).status_code == 422
