"""Database tests run against a freshly migrated database in the test Postgres (`make test-db`).

These are the sanctioned exception to "test through the HTTP API": they prove the database itself
enforces the schema rules (spec #1, Testing Decisions). Each test runs in a transaction that is
rolled back, so tests never see each other's rows.
"""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

import psycopg
import pytest
from psycopg.rows import dict_row

from app.db.provision import APP_ROLE, OWNER_ROLE, SUPPORT_ROLE, DatabaseSettings
from tests.db.seed import Seed

def _connection(settings: DatabaseSettings, role: str) -> Iterator[psycopg.Connection[dict[str, object]]]:
    with psycopg.connect(settings.role_url(role), row_factory=dict_row) as conn:
        # Open the transaction now, so `conn.transaction()` in a test is a savepoint, never a commit.
        conn.execute("SELECT 1")
        try:
            yield conn
        finally:
            conn.rollback()


@pytest.fixture
def app_db(database: DatabaseSettings) -> Iterator[psycopg.Connection[dict[str, object]]]:
    """Connected as vigil_app, the role the backend uses."""
    yield from _connection(database, APP_ROLE)


@pytest.fixture
def owner_db(database: DatabaseSettings) -> Iterator[psycopg.Connection[dict[str, object]]]:
    """Connected as vigil_owner, which has every privilege: proves triggers, not grants, do the refusing."""
    yield from _connection(database, OWNER_ROLE)


@pytest.fixture
def support_db(database: DatabaseSettings) -> Iterator[psycopg.Connection[dict[str, object]]]:
    yield from _connection(database, SUPPORT_ROLE)


@pytest.fixture
def seed(app_db: psycopg.Connection[dict[str, object]]) -> Seed:
    return Seed(app_db)


@pytest.fixture
def owner_seed(owner_db: psycopg.Connection[dict[str, object]]) -> Seed:
    return Seed(owner_db)


Rejects = Callable[[type[Exception]], AbstractContextManager[None]]


@pytest.fixture
def rejects(app_db: psycopg.Connection[dict[str, object]]) -> Rejects:
    return rejects_on(app_db)


def rejects_on(conn: psycopg.Connection[dict[str, object]]) -> Rejects:
    """`with rejects(CheckViolation): ...` asserts the database refuses, then carries on (savepoint)."""

    @contextmanager
    def check(error: type[Exception]) -> Iterator[None]:
        with pytest.raises(error):
            with conn.transaction():
                yield
                # Deferred constraint triggers fire now, inside the savepoint.
                conn.execute("SET CONSTRAINTS ALL IMMEDIATE")

    return check
