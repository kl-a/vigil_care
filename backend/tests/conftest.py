import base64
import os
import uuid
from collections.abc import Callable, Iterator

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import make_url
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.provision import DatabaseSettings, migrate, provision_roles
from app.main import create_app


TEST_ENCRYPTION_KEY = base64.b64encode(bytes([7] * 32)).decode()


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "dev_login_enabled": False,
        "session_secret": "test-session-secret-" + "x" * 32,
        # A fixed, test-only key (32 bytes of 0x07): never used outside tests.
        "encryption_key": TEST_ENCRYPTION_KEY,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def client_factory() -> Callable[..., TestClient]:
    def build(database_ok: bool = True, **overrides: object) -> TestClient:
        app = create_app(make_settings(**overrides), database_check=lambda: database_ok)
        return TestClient(app)

    return build


# --- A freshly migrated database in the test Postgres (`make test-db`), one per test run ---

ADMIN_URL = os.environ.get("VIGIL_TEST_DB_ADMIN_URL", "postgresql://vigil:vigil@localhost:55432/vigil")


@pytest.fixture(scope="session")
def database() -> Iterator[DatabaseSettings]:
    name = f"vigil_test_{uuid.uuid4().hex[:12]}"
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as error:
        pytest.fail(
            f"The test database isn't reachable at {ADMIN_URL}. Start it with `make test-db`.\n{error}"
        )
    with admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = make_url(ADMIN_URL).set(database=name).render_as_string(hide_password=False)
    settings = DatabaseSettings(admin_url=url)
    try:
        provision_roles(settings)
        migrate(settings)
        yield settings
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
