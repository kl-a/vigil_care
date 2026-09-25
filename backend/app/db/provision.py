"""Database roles and migrations (design doc §6.2, "Database roles and grants").

Provisioning needs the cluster admin and runs before migrations. It creates the roles and gives
`vigil_owner` the right to create objects in the database. The migrations, run as `vigil_owner`,
then grant each role exactly what it may do. The running app connects as `vigil_app`.

    python -m app.db.provision          # create/update roles, then migrate to head
"""

from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.core.config import ENV_FILES

OWNER_ROLE = "vigil_owner"
APP_ROLE = "vigil_app"
SUPPORT_ROLE = "vigil_support"
IDENTITY_ROLE = "identity_access"

ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"


class DatabaseSettings(BaseSettings):
    """Credentials for provisioning. The dev defaults are for synthetic local databases only."""

    model_config = SettingsConfigDict(env_prefix="VIGIL_DB_", env_file=ENV_FILES, extra="ignore")

    # A cluster admin, connected to the database to provision.
    admin_url: str = "postgresql://vigil:vigil@localhost:5432/vigil"
    owner_password: str = "vigil_owner_dev"
    app_password: str = "vigil_app_dev"
    support_password: str = "vigil_support_dev"

    def passwords(self) -> dict[str, str]:
        """Each login role and its password."""
        return {
            OWNER_ROLE: self.owner_password,
            APP_ROLE: self.app_password,
            SUPPORT_ROLE: self.support_password,
        }

    def role_url(self, role: str, driver: str = "postgresql") -> str:
        password = self.passwords()[role]
        url = make_url(self.admin_url).set(drivername=driver, username=role, password=password)
        return url.render_as_string(hide_password=False)


def provision_roles(settings: DatabaseSettings) -> None:
    """Idempotent: creates the roles if missing and resets their passwords."""
    with psycopg.connect(settings.admin_url, autocommit=True) as conn:
        existing = {row[0] for row in conn.execute("SELECT rolname FROM pg_roles")}
        for role, password in settings.passwords().items():
            verb = "ALTER" if role in existing else "CREATE"
            conn.execute(
                sql.SQL(verb + " ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )
        if IDENTITY_ROLE not in existing:
            conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(IDENTITY_ROLE)))
        conn.execute(
            sql.SQL("GRANT {} TO {}").format(sql.Identifier(IDENTITY_ROLE), sql.Identifier(APP_ROLE))
        )
        database = sql.Identifier(conn.info.dbname)
        conn.execute(sql.SQL("GRANT CONNECT, CREATE ON DATABASE {} TO {}").format(database, sql.Identifier(OWNER_ROLE)))
        conn.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}, {}").format(
                database, sql.Identifier(APP_ROLE), sql.Identifier(SUPPORT_ROLE)
            )
        )
        conn.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(OWNER_ROLE)))


def alembic_config(settings: DatabaseSettings) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    config.set_main_option(
        "sqlalchemy.url", settings.role_url(OWNER_ROLE, driver="postgresql+psycopg").replace("%", "%%")
    )
    return config


def migrate(settings: DatabaseSettings, revision: str = "head") -> None:
    command.upgrade(alembic_config(settings), revision)


def main() -> None:
    settings = DatabaseSettings()
    provision_roles(settings)
    migrate(settings)
    print("Database roles provisioned and schema migrated to head.")


if __name__ == "__main__":
    main()
