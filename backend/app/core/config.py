from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "test", "prod"]

# Signs dev session cookies. Refused outside dev, so a real secret must be set there.
DEV_SESSION_SECRET = "dev-only-session-secret-never-use-outside-dev"
MIN_SESSION_SECRET_LENGTH = 32


class StartupRefused(RuntimeError):
    """Raised when the configuration must never be allowed to run."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIGIL_", env_file=".env", extra="ignore")

    # Read from VIGIL_ENV (the documented name), not the prefix-derived VIGIL_ENVIRONMENT.
    environment: Environment = Field(default="dev", validation_alias=AliasChoices("VIGIL_ENV", "environment"))
    dev_login_enabled: bool = False
    database_url: str = "postgresql://vigil_app:vigil_app_dev@localhost:5432/vigil"
    vlm_worker_url: str | None = None
    session_secret: str = DEV_SESSION_SECRET

    @field_validator("session_secret")
    @classmethod
    def _unset_means_dev_default(cls, value: str) -> str:
        # Docker Compose passes an empty string when VIGIL_SESSION_SECRET isn't set.
        return value or DEV_SESSION_SECRET


def refuse_unsafe_startup(settings: Settings) -> None:
    """The dev login may exist only in dev, and prod isn't supported in the MVP."""
    if settings.dev_login_enabled and settings.environment != "dev":
        raise StartupRefused(
            f"The dev login is enabled in the '{settings.environment}' environment. "
            "It may only be enabled when VIGIL_ENV=dev."
        )
    if settings.environment != "dev" and (
        settings.session_secret == DEV_SESSION_SECRET or len(settings.session_secret) < MIN_SESSION_SECRET_LENGTH
    ):
        raise StartupRefused(
            f"The session secret in the '{settings.environment}' environment is the dev default or too short. "
            f"Set VIGIL_SESSION_SECRET to a random value of at least {MIN_SESSION_SECRET_LENGTH} characters."
        )
    if settings.environment == "prod":
        raise StartupRefused("VIGIL_ENV=prod is not supported in the MVP (synthetic data only; dev and test).")
