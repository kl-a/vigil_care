"""Patients with encrypted Patient Identity (#8). Everyone in the Practice but developer admins sees them."""

import re
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn, dev_login
from tests.db.seed import Seed

# Synthetic identity (frontend brief §10). 02 5550 / 0491 570 1xx numbers are reserved for fiction; Medicare
# numbers and IHIs starting with zeros are never issued.
JANE = {
    "given_name": "Jane",
    "family_name": "Citizen",
    "dob": "1962-04-03",
    "medicare_number": "0000 12345 1",
    "medicare_irn": "1",
    "ihi": "0000 0000 0000 0042",
    "mrn": "1002003",
    "address": "10 Example Ave, Sydney NSW 2000",
    "phone": "02 5550 0142",
    "mobile": "0491 570 156",
    "email": "jane.citizen@example.com",
    "next_of_kin_name": "John Citizen (husband)",
    "next_of_kin_phone": "0491 570 157",
}
ENCRYPTED = ("medicare_number", "ihi", "address", "phone", "mobile", "email", "next_of_kin_phone")


def patient(**overrides: Any) -> dict[str, Any]:
    return {**JANE, "mrn": str(uuid.uuid4().int % 10**7), **overrides}


def create(client: TestClient, identity: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/patients", json=identity)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.parametrize("job_title", ["clinician", "trial_coordinator", "secretary"])
def test_staff_create_a_patient_with_their_full_identity(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    identity = patient()
    created = create(client, identity)
    assert re.fullmatch(r"VG-\d{4,}", created["pseudonym"])
    assert created["identity"] == identity
    assert client.get(f"/patients/{created['id']}").json()["identity"] == identity


def test_each_patient_gets_a_new_pseudonym(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary")
    pseudonyms = [create(client, patient())["pseudonym"] for _ in range(3)]
    assert len(set(pseudonyms)) == 3
    assert [int(p[3:]) for p in pseudonyms] == sorted(int(p[3:]) for p in pseudonyms)


def test_sensitive_fields_are_ciphertext_in_the_database(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("clinician")
    created = create(client, patient(medicare_number="0000 99999 1"))
    row = committed.conn.execute(
        "SELECT * FROM identity.patient_identity WHERE patient_id = %s", [created["id"]]
    ).fetchone()
    columns = [c.name for c in committed.conn.execute("SELECT * FROM identity.patient_identity LIMIT 0").description or []]
    stored = dict(zip(columns, row or ()))
    for field in ENCRYPTED:
        ciphertext = bytes(stored[f"{field}_encrypted"])
        assert JANE[field].encode() not in ciphertext and b"99999" not in ciphertext, field
    # The audit trail doesn't give the identity away either.
    audit = committed.conn.execute(
        "SELECT before::text, after::text FROM verification WHERE subject_table = 'patient' AND subject_id = %s", [created["id"]]
    ).fetchall()
    assert audit and all("99999" not in str(entry) and "Citizen" not in str(entry) for entry in audit)


def test_the_patient_list_is_searched_by_name_or_mrn(sign_in: SignIn) -> None:
    client, _ = sign_in("trial_coordinator")
    create(client, patient())
    create(client, patient(given_name="Sam", family_name="Example", mrn="1002017"))
    create(client, patient(given_name="Robin", family_name="Sample"))

    names = lambda q: [p["display_name"] for p in client.get("/patients", params={"q": q} if q else {}).json()]  # noqa: E731
    assert names("") == ["Jane Citizen", "Sam Example", "Robin Sample"]
    assert names("citi") == ["Jane Citizen"]
    assert names("sam") == ["Sam Example", "Robin Sample"]
    assert names("sam example") == ["Sam Example"]
    assert names("1002017") == ["Sam Example"]
    row = client.get("/patients", params={"q": "citizen"}).json()[0]
    assert (row["dob"], row["pseudonym"][:3]) == ("1962-04-03", "VG-")


def test_editing_identity_is_a_verification_with_before_and_after(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary", display_name="Jordan Park (synthetic)")
    created = create(client, patient())
    changed = client.patch(f"/patients/{created['id']}/identity", json={"mobile": "0491 570 158", "address": "12 Example Ave"})
    assert changed.status_code == 200
    assert changed.json()["identity"]["mobile"] == "0491 570 158"

    history = client.get(f"/patients/{created['id']}").json()["history"]
    latest = history[0]
    assert latest["action"] == "edit"
    assert (latest["by_display_name"], latest["by_job_title"]) == ("Jordan Park (synthetic)", "secretary")
    assert latest["before"] == {"mobile": JANE["mobile"], "address": JANE["address"]}
    assert latest["after"] == {"mobile": "0491 570 158", "address": "12 Example Ave"}
    assert latest["at"]
    assert history[-1]["before"] is None  # created


def test_clearing_an_optional_field_and_saving_nothing_new(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    created = create(client, patient())
    cleared = client.patch(f"/patients/{created['id']}/identity", json={"email": ""})
    assert cleared.json()["identity"]["email"] is None
    client.patch(f"/patients/{created['id']}/identity", json={"given_name": "Jane"})
    assert len(client.get(f"/patients/{created['id']}").json()["history"]) == 2


def test_developer_admins_are_refused_every_patient_endpoint(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    someone = committed.patient(ids["practice"])
    for method, path, body in [
        ("GET", "/patients", None),
        ("POST", "/patients", patient()),
        ("GET", f"/patients/{someone}", None),
        ("PATCH", f"/patients/{someone}/identity", {"phone": "02 5550 0000"}),
    ]:
        response = client.request(method, path, json=body)
        assert response.status_code == 403, f"{method} {path}"


def test_another_practice_cant_read_or_write_our_patients(sign_in: SignIn) -> None:
    ours, _ = sign_in("clinician")
    theirs, _ = sign_in("clinician")
    created = create(ours, patient())
    assert theirs.get("/patients").json() == []
    assert theirs.get(f"/patients/{created['id']}").status_code == 404
    assert theirs.patch(f"/patients/{created['id']}/identity", json={"phone": "02 5550 0000"}).status_code == 404
    assert ours.get(f"/patients/{created['id']}").json()["identity"]["phone"] == JANE["phone"]


@pytest.mark.parametrize(
    "bad",
    [
        {"given_name": " "},
        {"family_name": ""},
        {"medicare_number": "1234"},
        {"medicare_irn": "0"},
        {"ihi": "0000 0000"},
        {"email": "not-an-email"},
        {"dob": "2999-01-01"},
    ],
)
def test_invalid_identity_is_refused(sign_in: SignIn, bad: dict[str, Any]) -> None:
    client, _ = sign_in("clinician")
    assert client.post("/patients", json=patient(**bad)).status_code == 422


def test_details_sealed_under_another_key_are_reported_not_leaked(sign_in: SignIn, api: Any, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    created = create(client, patient())
    other_key = api(encryption_key="b3RoZXIta2V5LW90aGVyLWtleS1vdGhlci1rZXktISE=")
    assert dev_login(other_key, ids["user"], ids["practice"]).status_code == 200
    refused = other_key.get(f"/patients/{created['id']}")
    assert refused.status_code == 500
    assert refused.json()["detail"] == "Some Patient details can't be decrypted with the configured encryption key."


# --- Removing a Patient (#17): soft delete with a reason, never erased ------------------------------


def test_removing_a_patient_needs_a_reason_and_hides_them(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("secretary", display_name="Jordan Park (synthetic)")
    created = create(client, patient())
    assert client.request("DELETE", f"/patients/{created['id']}", json={"reason": "  "}).status_code == 422
    assert client.request("DELETE", f"/patients/{created['id']}", json={"reason": "Duplicate record"}).status_code == 204

    assert client.get("/patients").json() == []
    assert client.get("/patients", params={"q": "citizen"}).json() == []
    row = committed.conn.execute(
        "SELECT deleted_at IS NOT NULL, deleted_reason FROM patient WHERE id = %s", [created["id"]]
    ).fetchone()
    assert row == (True, "Duplicate record")  # still there: removed, never erased
    audit = committed.conn.execute(
        "SELECT action, reason FROM verification WHERE subject_table = 'patient' AND subject_id = %s AND action = 'delete'",
        [created["id"]],
    ).fetchone()
    assert audit == ("delete", "Duplicate record")


def test_a_removed_patients_url_says_who_removed_them_and_why(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary", display_name="Jordan Park (synthetic)")
    created = create(client, patient())
    client.request("DELETE", f"/patients/{created['id']}", json={"reason": "Duplicate record"})

    opened = client.get(f"/patients/{created['id']}")
    assert opened.status_code == 410
    detail = opened.json()["detail"]
    assert detail.startswith("This Patient was removed by Jordan Park (synthetic) (Secretary) on ")
    assert detail.endswith(": Duplicate record")
    assert client.patch(f"/patients/{created['id']}/identity", json={"phone": "02 5550 0000"}).status_code == 410
    assert client.request("DELETE", f"/patients/{created['id']}", json={"reason": "Again"}).status_code == 410


def test_developer_admins_cant_remove_patients(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    someone = committed.patient(ids["practice"])
    assert client.request("DELETE", f"/patients/{someone}", json={"reason": "x"}).status_code == 403


def test_another_practice_cant_remove_our_patients(sign_in: SignIn) -> None:
    ours, _ = sign_in("clinician")
    theirs, _ = sign_in("clinician")
    created = create(ours, patient())
    assert theirs.request("DELETE", f"/patients/{created['id']}", json={"reason": "x"}).status_code == 404
    assert ours.get(f"/patients/{created['id']}").status_code == 200


def test_no_endpoint_hard_deletes_patient_data(api: Any) -> None:
    """Every DELETE on a Patient route soft-deletes and needs a reason (a Removal body)."""
    spec = api().app.openapi()
    for path, methods in spec["paths"].items():
        if path.startswith("/patients") and "delete" in methods:
            body = methods["delete"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            assert body.endswith("/Removal"), path
