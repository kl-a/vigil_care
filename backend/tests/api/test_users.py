"""User Management basics (#6): who may manage Users, and every change is a Verification."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SignIn, dev_login
from tests.db.seed import Seed


def new_user(**overrides: Any) -> dict[str, Any]:
    """Usernames are unique across Vigil, and API tests share one database: each gets a fresh one."""
    return {"username": f"riley.{uuid.uuid4().hex[:8]}", "display_name": "Riley Hart (synthetic)", "job_title": "secretary", **overrides}


@pytest.mark.parametrize("job_title", ["clinician", "secretary", "developer_admin"])
def test_clinicians_secretaries_and_developer_admins_manage_users(sign_in: SignIn, job_title: str) -> None:
    client, _ = sign_in(job_title)
    new = new_user()
    created = client.post("/users", json=new)
    assert created.status_code == 201
    assert created.json()["job_title"] == "secretary"
    assert new["username"] in {u["username"] for u in client.get("/users").json()}


def test_trial_coordinators_cant_manage_users(sign_in: SignIn) -> None:
    client, _ = sign_in("trial_coordinator")
    assert client.get("/users").status_code == 403
    assert client.post("/users", json=new_user()).status_code == 403


def test_the_list_shows_job_title_status_linked_provider_and_last_login(sign_in: SignIn) -> None:
    client, ids = sign_in("clinician", display_name="Dr Alex Rivera (synthetic)")
    me = next(u for u in client.get("/users").json() if u["id"] == str(ids["user"]))
    assert me["display_name"] == "Dr Alex Rivera (synthetic)"
    assert me["job_title"] == "clinician"
    assert me["is_active"] is True
    assert me["provider_id"] is None
    assert me["last_login_at"] is not None  # set by the dev login


def test_users_of_another_practice_are_invisible(sign_in: SignIn, committed: Seed) -> None:
    client, _ = sign_in("secretary")
    elsewhere = committed.user(committed.practice(), display_name="Someone Else")
    assert str(elsewhere) not in {u["id"] for u in client.get("/users").json()}
    assert client.get(f"/users/{elsewhere}").status_code == 404
    assert client.patch(f"/users/{elsewhere}", json={"job_title": "clinician"}).status_code == 404


def test_someone_already_in_this_practice_cant_be_added_again(sign_in: SignIn) -> None:
    client, _ = sign_in("secretary")
    new = new_user()
    assert client.post("/users", json=new).status_code == 201
    duplicate = client.post("/users", json=new)
    assert duplicate.status_code == 409
    assert "already" in duplicate.json()["detail"]


def test_changing_a_job_title_records_a_verification(sign_in: SignIn) -> None:
    client, ids = sign_in("secretary", display_name="Jordan Park (synthetic)")
    user = client.post("/users", json=new_user()).json()

    changed = client.patch(f"/users/{user['id']}", json={"job_title": "developer_admin", "reason": "Joining IT support"})
    assert changed.status_code == 200
    assert changed.json()["job_title"] == "developer_admin"

    history = client.get(f"/users/{user['id']}").json()["history"]
    latest = history[0]
    assert latest["action"] == "edit"
    assert latest["by_display_name"] == "Jordan Park (synthetic)"
    assert latest["by_job_title"] == "secretary"
    assert latest["before"] == {"job_title": "secretary"}
    assert latest["after"] == {"job_title": "developer_admin"}
    assert latest["reason"] == "Joining IT support"
    assert latest["reauthenticated"] is False
    assert latest["at"]


def test_creating_a_user_records_the_job_title_granted(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    user = client.post("/users", json=new_user()).json()
    history = client.get(f"/users/{user['id']}").json()["history"]
    assert [(h["before"], h["after"]["job_title"]) for h in history] == [(None, "secretary")]


def test_deactivating_needs_a_reason_and_records_a_verification(sign_in: SignIn) -> None:
    client, _ = sign_in("developer_admin")
    user = client.post("/users", json=new_user()).json()

    assert client.patch(f"/users/{user['id']}", json={"is_active": False}).status_code == 422
    assert client.patch(f"/users/{user['id']}", json={"is_active": False, "reason": "  "}).status_code == 422
    done = client.patch(f"/users/{user['id']}", json={"is_active": False, "reason": "Left the Practice"})
    assert done.status_code == 200 and done.json()["is_active"] is False

    latest = client.get(f"/users/{user['id']}").json()["history"][0]
    assert (latest["before"], latest["after"], latest["reason"]) == ({"is_active": True}, {"is_active": False}, "Left the Practice")


def test_a_deactivated_user_cant_sign_in_and_keeps_their_verifications(sign_in: SignIn, api: object) -> None:
    admin, ids = sign_in("secretary")
    user = admin.post("/users", json=new_user(job_title="clinician")).json()

    # The new User signs in and changes someone's Job Title, leaving a Verification behind.
    client: TestClient = api()  # type: ignore[operator]
    assert dev_login(client, user["id"], ids["practice"]).status_code == 200
    other = client.post("/users", json=new_user()).json()
    client.patch(f"/users/{other['id']}", json={"job_title": "trial_coordinator"})

    admin.patch(f"/users/{user['id']}", json={"is_active": False, "reason": "Left the Practice"})
    assert client.get("/auth/me").status_code == 401
    assert user["id"] not in {u["id"] for u in client.get("/auth/dev-login/users").json()}
    signed = admin.get(f"/users/{other['id']}").json()["history"][0]
    assert signed["by_display_name"] == "Riley Hart (synthetic)"
    assert signed["by_job_title"] == "clinician"


def test_you_cant_change_your_own_job_title_or_deactivate_yourself(sign_in: SignIn) -> None:
    client, ids = sign_in("developer_admin")
    me = f"/users/{ids['user']}"
    assert client.patch(me, json={"job_title": "clinician"}).status_code == 409
    assert client.patch(me, json={"is_active": False, "reason": "Oops"}).status_code == 409


def test_job_titles_and_usernames_are_validated(sign_in: SignIn) -> None:
    client, _ = sign_in("clinician")
    assert client.post("/users", json=new_user(job_title="superuser")).status_code == 422
    assert client.post("/users", json=new_user(username="Has Spaces")).status_code == 422
    assert client.post("/users", json=new_user(display_name=" ")).status_code == 422


def test_a_user_is_linked_to_their_own_provider_record(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("developer_admin")
    doctor = client.post("/users", json=new_user(job_title="clinician")).json()
    provider = committed.provider(ids["practice"], title="Dr", first_name="Riley", last_name="Hart")

    linked = client.patch(f"/users/{doctor['id']}", json={"provider_id": str(provider)})
    assert linked.status_code == 200
    assert (linked.json()["provider_id"], linked.json()["provider_name"]) == (str(provider), "Dr Riley Hart")
    latest = client.get(f"/users/{doctor['id']}").json()["history"][0]
    assert (latest["before"], latest["after"]) == ({"provider_id": None}, {"provider_id": str(provider)})

    unlinked = client.patch(f"/users/{doctor['id']}", json={"provider_id": None})
    assert (unlinked.json()["provider_id"], unlinked.json()["provider_name"]) == (None, None)


def test_you_may_link_your_own_provider_record(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("clinician")
    provider = committed.provider(ids["practice"])
    assert client.patch(f"/users/{ids['user']}", json={"provider_id": str(provider)}).status_code == 200


def test_only_this_practices_live_providers_can_be_linked(sign_in: SignIn, committed: Seed) -> None:
    client, ids = sign_in("secretary")
    user = client.post("/users", json=new_user()).json()
    elsewhere = committed.provider(committed.practice())
    refused = client.patch(f"/users/{user['id']}", json={"provider_id": str(elsewhere)})
    assert refused.status_code == 422
    assert refused.json()["detail"] == "No such Provider in this Practice."
