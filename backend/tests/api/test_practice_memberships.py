"""Practice Memberships (#24): one login, several Practices. A User acts as one Practice at a time."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import SignIn, dev_login
from tests.db.seed import Seed


def two_practices(committed: Seed, harbourside: str = "clinician", northside: str = "clinician") -> dict[str, Any]:
    """Dr Rivera works at two Practices, with a Job Title at each."""
    first = committed.insert("practice", name="Harbourside (test)")
    second = committed.insert("practice", name="Northside (test)")
    doctor = committed.user(first, job_title=harbourside, display_name="Dr Rivera", username=f"rivera.{uuid.uuid4().hex[:8]}")
    committed.member(second, doctor, job_title=northside)
    return {"first": first, "second": second, "doctor": doctor}


def test_the_dev_login_lists_each_membership_as_its_own_choice(api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed)
    choices = [c for c in api().get("/auth/dev-login/users").json() if c["id"] == str(ids["doctor"])]
    assert sorted((c["practice_name"], c["practice_id"]) for c in choices) == [
        ("Harbourside (test)", str(ids["first"])),
        ("Northside (test)", str(ids["second"])),
    ]


def test_signing_in_acts_as_the_chosen_practice_with_its_job_title(api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed, harbourside="clinician", northside="secretary")
    at_first, at_second = api(), api()
    dev_login(at_first, ids["doctor"], ids["first"])
    dev_login(at_second, ids["doctor"], ids["second"])

    first, second = at_first.get("/auth/me").json(), at_second.get("/auth/me").json()
    assert (first["id"], first["practice_name"], first["job_title"]) == (str(ids["doctor"]), "Harbourside (test)", "clinician")
    assert (second["id"], second["practice_name"], second["job_title"]) == (str(ids["doctor"]), "Northside (test)", "secretary")


def test_each_practices_data_is_seen_only_when_acting_in_it(api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed)
    colleague = committed.user(ids["second"], display_name="Northside colleague")
    client = api()

    dev_login(client, ids["doctor"], ids["first"])
    assert client.get("/practice").json()["name"] == "Harbourside (test)"
    assert str(colleague) not in {u["id"] for u in client.get("/users").json()}

    dev_login(client, ids["doctor"], ids["second"])
    assert client.get("/practice").json()["name"] == "Northside (test)"
    assert str(colleague) in {u["id"] for u in client.get("/users").json()}


def test_permissions_follow_the_job_title_held_in_the_current_practice(api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed, harbourside="clinician", northside="trial_coordinator")
    client = api()
    dev_login(client, ids["doctor"], ids["first"])
    assert client.get("/users").status_code == 200
    dev_login(client, ids["doctor"], ids["second"])
    assert client.get("/users").status_code == 403


def test_you_cant_sign_in_to_a_practice_you_dont_belong_to(api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed)
    stranger = committed.practice()
    client = api()
    assert dev_login(client, ids["doctor"], stranger).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_deactivation_at_one_practice_leaves_the_other_membership_working(sign_in: SignIn, api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed)
    admin, _ = sign_in("secretary", practice=ids["first"])
    at_first, at_second = api(), api()
    dev_login(at_first, ids["doctor"], ids["first"])
    dev_login(at_second, ids["doctor"], ids["second"])

    assert admin.patch(f"/users/{ids['doctor']}", json={"is_active": False, "reason": "Moved to Northside"}).status_code == 200

    assert at_first.get("/auth/me").status_code == 401
    assert at_second.get("/auth/me").json()["practice_id"] == str(ids["second"])
    assert dev_login(api(), ids["doctor"], ids["first"]).status_code == 401
    choices = {c["practice_id"] for c in api().get("/auth/dev-login/users").json() if c["id"] == str(ids["doctor"])}
    assert choices == {str(ids["second"])}


def test_a_job_title_change_affects_only_this_practice(sign_in: SignIn, api: Callable[..., TestClient], committed: Seed) -> None:
    ids = two_practices(committed)
    admin, _ = sign_in("secretary", practice=ids["second"])
    assert admin.patch(f"/users/{ids['doctor']}", json={"job_title": "trial_coordinator"}).status_code == 200

    client = api()
    dev_login(client, ids["doctor"], ids["first"])
    assert client.get("/auth/me").json()["job_title"] == "clinician"
    dev_login(client, ids["doctor"], ids["second"])
    assert client.get("/auth/me").json()["job_title"] == "trial_coordinator"


def test_adding_someone_with_a_login_elsewhere_by_username(sign_in: SignIn, api: Callable[..., TestClient], committed: Seed) -> None:
    elsewhere = committed.practice()
    username = f"rivera.{uuid.uuid4().hex[:8]}"
    doctor = committed.user(elsewhere, display_name="Dr Rivera", username=username)
    admin, ids = sign_in("secretary")

    added = admin.post("/users", json={"username": username, "job_title": "clinician"})
    assert added.status_code == 201
    assert added.json()["id"] == str(doctor)
    assert added.json()["display_name"] == "Dr Rivera"  # their own name comes with their login

    # Nothing about their other Practices shows here.
    detail = admin.get(f"/users/{doctor}").json()
    assert str(elsewhere) not in str(detail)
    assert [(h["before"], h["after"]) for h in detail["history"]] == [(None, {"job_title": "clinician", "username": username})]

    # And they can now sign in here, as a clinician.
    assert dev_login(api(), doctor, ids["practice"]).json()["job_title"] == "clinician"


def test_a_brand_new_login_needs_a_display_name(sign_in: SignIn) -> None:
    admin, _ = sign_in("secretary")
    refused = admin.post("/users", json={"username": f"new.{uuid.uuid4().hex[:8]}", "job_title": "secretary"})
    assert refused.status_code == 422
    assert "display name" in refused.json()["detail"]
