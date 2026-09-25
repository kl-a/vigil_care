"""Migration 0003 (#24) carries existing Users over to Practice Memberships, and back while that's lossless."""

import uuid
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from psycopg import sql
from alembic import command
from psycopg.errors import ForeignKeyViolation
from psycopg.rows import dict_row
from sqlalchemy import make_url
from sqlalchemy.exc import ProgrammingError

from app.db.provision import OWNER_ROLE, DatabaseSettings, alembic_config, migrate, provision_roles
from tests.conftest import ADMIN_URL


@pytest.fixture
def before_memberships() -> Iterator[DatabaseSettings]:
    """A throwaway database migrated only as far as 0002, when a User belonged to one Practice."""
    name = f"vigil_migration_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    settings = DatabaseSettings(admin_url=make_url(ADMIN_URL).set(database=name).render_as_string(hide_password=False))
    try:
        provision_roles(settings)
        migrate(settings, "0002_oncology")
        yield settings
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def _owner(settings: DatabaseSettings) -> psycopg.Connection[dict[str, Any]]:
    return psycopg.connect(settings.role_url(OWNER_ROLE), autocommit=True, row_factory=dict_row)


def _id(conn: psycopg.Connection[dict[str, Any]], query: str | sql.Composed, params: list[Any] | None = None) -> Any:
    row = conn.execute(query, params).fetchone()
    assert row is not None
    return row["id"]


PRACTICE = "INSERT INTO practice (name) VALUES ('Synthetic') RETURNING id"
LOGIN = "INSERT INTO \"user\" (username, display_name, password_hash) VALUES (%s, %s, 'x') RETURNING id"


def _old_user(conn: psycopg.Connection[dict[str, Any]], practice: Any, username: str, job_title: str, **values: Any) -> Any:
    columns = {"practice_id": practice, "username": username, "display_name": username, "password_hash": "x", "job_title": job_title, **values}
    query = sql.SQL('INSERT INTO "user" ({}) VALUES ({}) RETURNING id').format(
        sql.SQL(", ").join(map(sql.Identifier, columns)), sql.SQL(", ").join(sql.Placeholder() * len(columns))
    )
    return _id(conn, query, list(columns.values()))


def test_each_user_becomes_a_login_with_one_membership(before_memberships: DatabaseSettings) -> None:
    with _owner(before_memberships) as conn:
        practice = _id(conn, PRACTICE)
        clinician = _old_user(conn, practice, "kim", "clinician")
        _old_user(conn, practice, "lee", "secretary", is_active=False)
        conn.execute(
            "INSERT INTO verification (practice_id, subject_table, subject_id, user_id, job_title_at_time, action)"
            " VALUES (%s, 'user', %s, %s, 'clinician', 'edit')",
            [practice, clinician, clinician],
        )

    migrate(before_memberships)

    with _owner(before_memberships) as conn:
        rows = conn.execute(
            'SELECT u.username, m.practice_id, m.job_title, m.is_active FROM practice_membership m JOIN "user" u ON u.id = m.user_id ORDER BY 1'
        ).fetchall()
        assert rows == [
            {"username": "kim", "practice_id": practice, "job_title": "clinician", "is_active": True},
            {"username": "lee", "practice_id": practice, "job_title": "secretary", "is_active": False},
        ]
        # The Verification still points at kim, now through their Membership: a stranger can't sign one.
        stranger = _id(conn, LOGIN, ["stranger", "Stranger"])
        with pytest.raises(ForeignKeyViolation):
            conn.execute(
                "INSERT INTO verification (practice_id, subject_table, subject_id, user_id, job_title_at_time, action)"
                " VALUES (%s, 'user', %s, %s, 'clinician', 'edit')",
                [practice, clinician, stranger],
            )


def test_downgrading_refuses_to_lose_a_second_membership(before_memberships: DatabaseSettings) -> None:
    migrate(before_memberships)
    with _owner(before_memberships) as conn:
        first, second = _id(conn, PRACTICE), _id(conn, PRACTICE)
        user = _id(conn, LOGIN, ["kim", "Kim"])
        for practice in (first, second):
            conn.execute("INSERT INTO practice_membership (practice_id, user_id, job_title) VALUES (%s, %s, 'clinician')", [practice, user])

    with pytest.raises(ProgrammingError, match="several Practices"):
        command.downgrade(alembic_config(before_memberships), "0002_oncology")


def test_downgrading_one_membership_each_restores_the_old_user(before_memberships: DatabaseSettings) -> None:
    migrate(before_memberships)
    with _owner(before_memberships) as conn:
        practice = _id(conn, PRACTICE)
        user = _id(conn, LOGIN, ["kim", "Kim"])
        conn.execute("INSERT INTO practice_membership (practice_id, user_id, job_title) VALUES (%s, %s, 'secretary')", [practice, user])

    command.downgrade(alembic_config(before_memberships), "0002_oncology")

    with _owner(before_memberships) as conn:
        assert conn.execute('SELECT practice_id, job_title FROM "user"').fetchall() == [{"practice_id": practice, "job_title": "secretary"}]
