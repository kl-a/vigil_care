"""API tests drive the Vigil HTTP API against a real, freshly migrated database (spec #1 Testing Decisions)."""

from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db.provision import APP_ROLE, DatabaseSettings
from app.main import create_app
from tests.conftest import make_settings
from tests.db.seed import Seed


@pytest.fixture
def committed(database: DatabaseSettings) -> Iterator[Seed]:
    """Rows the API can see: committed as vigil_app. Each test makes its own Practice, so tests don't collide."""
    with psycopg.connect(database.role_url(APP_ROLE), autocommit=True) as conn:
        yield Seed(conn)


@pytest.fixture
def api(database: DatabaseSettings) -> Callable[..., TestClient]:
    def build(**overrides: Any) -> TestClient:
        values: dict[str, Any] = {
            "environment": "dev",
            "dev_login_enabled": True,
            "database_url": database.role_url(APP_ROLE),
        }
        values.update(overrides)
        return TestClient(create_app(make_settings(**values), database_check=lambda: True))

    return build


SignIn = Callable[..., tuple[TestClient, dict[str, Any]]]


@pytest.fixture
def sign_in(api: Callable[..., TestClient], committed: Seed) -> SignIn:
    """A client signed in (dev login) as a new User with the given Job Title, in a fresh Practice by default."""

    def go(job_title: str = "clinician", practice: Any = None, **user: Any) -> tuple[TestClient, dict[str, Any]]:
        practice = practice or committed.practice()
        user_id = committed.user(practice, job_title=job_title, **user)
        client = api()
        assert client.post("/auth/dev-login", json={"user_id": str(user_id)}).status_code == 200
        return client, {"practice": practice, "user": user_id}

    return go
