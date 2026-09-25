"""Dev login as a seeded User (#13): in dev you pick who you are; every request then runs as that User."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.api.conftest import dev_login
from tests.db.seed import Seed

PUBLIC_PATHS = {"/health", "/auth/dev-login/users", "/auth/dev-login"}


def test_the_dev_login_lists_active_users_with_their_job_titles(api: Callable[..., TestClient], committed: Seed) -> None:
    practice = committed.practice()
    clinician = committed.user(practice, job_title="clinician", display_name="Dr Alex Rivera")
    committed.user(practice, job_title="secretary", display_name="Former Secretary", is_active=False)

    users = api().get("/auth/dev-login/users").json()

    chosen = next(u for u in users if u["id"] == str(clinician))
    assert chosen["display_name"] == "Dr Alex Rivera"
    assert chosen["job_title"] == "clinician"
    assert chosen["practice_id"] == str(practice)
    assert chosen["practice_name"] == "Synthetic Oncology Practice"
    assert "Former Secretary" not in {u["display_name"] for u in users}


def test_choosing_a_user_starts_a_session_as_that_user(api: Callable[..., TestClient], committed: Seed) -> None:
    practice = committed.practice()
    secretary = committed.user(practice, job_title="secretary", display_name="Jordan Park")
    client = api()

    login = dev_login(client, secretary, practice)
    assert login.status_code == 200

    me = client.get("/auth/me").json()
    assert me["id"] == str(secretary)
    assert me["display_name"] == "Jordan Park"
    assert me["job_title"] == "secretary"
    assert me["practice_id"] == str(practice)


def test_without_a_session_you_are_not_signed_in(api: Callable[..., TestClient]) -> None:
    assert api().get("/auth/me").status_code == 401


def test_a_deactivated_or_unknown_user_cant_be_chosen(api: Callable[..., TestClient], committed: Seed) -> None:
    practice = committed.practice()
    inactive = committed.user(practice, is_active=False)
    client = api()
    assert dev_login(client, inactive, practice).status_code == 401
    assert dev_login(client, "00000000-0000-0000-0000-000000000000", practice).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_a_user_deactivated_mid_session_is_signed_out(api: Callable[..., TestClient], committed: Seed) -> None:
    practice = committed.practice()
    user = committed.user(practice)
    client = api()
    dev_login(client, user, practice)
    committed.conn.execute("UPDATE practice_membership SET is_active = false WHERE user_id = %s", [user])
    assert client.get("/auth/me").status_code == 401


def test_logging_out_ends_the_session(api: Callable[..., TestClient], committed: Seed) -> None:
    practice = committed.practice()
    user = committed.user(practice)
    client = api()
    dev_login(client, user, practice)
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_the_dev_login_doesnt_exist_outside_dev(api: Callable[..., TestClient]) -> None:
    client = api(environment="test", dev_login_enabled=False)
    assert client.get("/auth/dev-login/users").status_code == 404
    assert dev_login(client, "00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000000").status_code == 404


def test_the_dev_login_doesnt_exist_when_disabled_in_dev(api: Callable[..., TestClient]) -> None:
    assert api(dev_login_enabled=False).get("/auth/dev-login/users").status_code == 404


def test_every_endpoint_except_login_and_health_requires_a_session(api: Callable[..., TestClient]) -> None:
    client = api()
    paths = client.app.openapi()["paths"]  # type: ignore[attr-defined]
    guarded = [(path, method.upper()) for path, methods in paths.items() if path not in PUBLIC_PATHS for method in methods]
    assert guarded, "expected at least /auth/me and /auth/logout"
    for path, method in guarded:
        response = client.request(method, path.replace("{", "").replace("}", ""))
        assert response.status_code == 401, f"{method} {path} answered {response.status_code} without a session"


def test_api_docs_exist_only_in_dev(api: Callable[..., TestClient]) -> None:
    assert api().get("/openapi.json").status_code == 200
    outside_dev = api(environment="test", dev_login_enabled=False, session_secret="s" * 48)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert outside_dev.get(path).status_code == 404
