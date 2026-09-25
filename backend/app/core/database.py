from collections.abc import Callable
from typing import Any

import psycopg
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import ORMExecuteState, Session, sessionmaker, with_loader_criteria

from app.core.base_model import Entity

DatabaseCheck = Callable[[], bool]

# Pass `execution_options(include_deleted=True)` to see soft-deleted rows (e.g. audit views).
INCLUDE_DELETED = "include_deleted"


def postgres_check(database_url: str, timeout_seconds: int = 2) -> DatabaseCheck:
    def check() -> bool:
        try:
            with psycopg.connect(database_url, connect_timeout=timeout_seconds) as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    return check


def session_factory(database_url: str) -> sessionmaker[Session]:
    url = make_url(database_url).set(drivername="postgresql+psycopg")
    return sessionmaker(create_engine(url))


@event.listens_for(Session, "do_orm_execute")
def _exclude_soft_deleted(state: ORMExecuteState) -> None:
    """Default queries exclude soft-deleted rows (design doc §6.2)."""
    if state.is_select and not state.is_column_load and not state.is_relationship_load:
        if not state.execution_options.get(INCLUDE_DELETED, False):
            criteria: Any = lambda cls: cls.deleted_at.is_(None)  # noqa: E731
            state.statement = state.statement.options(
                with_loader_criteria(Entity, criteria, include_aliases=True)
            )
