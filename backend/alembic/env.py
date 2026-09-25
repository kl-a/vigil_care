"""Alembic environment. Migrations run as vigil_owner; `python -m app.db.provision` sets the URL."""

from typing import Any

from alembic import context
from sqlalchemy import create_engine

from app.core.base_model import IDENTITY_SCHEMA
from app.db.metadata import metadata
from app.db.provision import OWNER_ROLE, DatabaseSettings

SCHEMAS = {None, "public", IDENTITY_SCHEMA}


def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    if type_ == "schema":
        return name in SCHEMAS
    return True


def run_migrations_online() -> None:
    url = context.config.get_main_option("sqlalchemy.url") or DatabaseSettings().role_url(
        OWNER_ROLE, driver="postgresql+psycopg"
    )
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,
            include_schemas=True,
            include_name=include_name,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
