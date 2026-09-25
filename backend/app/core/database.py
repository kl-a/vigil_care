from collections.abc import Callable, Iterator
import psycopg
from fastapi import Request
from sqlalchemy import ColumnElement, create_engine, event
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


def db_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one Session per request, committed if the request succeeds."""
    make_session: sessionmaker[Session] = request.app.state.sessionmaker
    with make_session.begin() as session:
        yield session


@event.listens_for(Session, "do_orm_execute")
def _exclude_soft_deleted(state: ORMExecuteState) -> None:
    """Default queries exclude soft-deleted rows (design doc §6.2)."""
    if state.is_select and not state.is_column_load and not state.is_relationship_load:
        if not state.execution_options.get(INCLUDE_DELETED, False):
            state.statement = state.statement.options(
                with_loader_criteria(Entity, _not_deleted, include_aliases=True)
            )


def _not_deleted(entity: type[Entity]) -> ColumnElement[bool]:
    return entity.deleted_at.is_(None)
