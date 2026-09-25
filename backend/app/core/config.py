from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["dev", "test", "prod"]


class StartupRefused(RuntimeError):
    """Raised when the configuration must never be allowed to run."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIGIL_", env_file=".env", extra="ignore")

    # Read from VIGIL_ENV (the documented name), not the prefix-derived VIGIL_ENVIRONMENT.
    environment: Environment = Field(default="dev", validation_alias=AliasChoices("VIGIL_ENV", "environment"))
    dev_login_enabled: bool = False
    database_url: str = "postgresql://vigil:vigil@localhost:5432/vigil"
    vlm_worker_url: str | None = None


def refuse_unsafe_startup(settings: Settings) -> None:
    """The dev login may exist only in dev, and prod isn't supported in the MVP."""
    if settings.dev_login_enabled and settings.environment != "dev":
        raise StartupRefused(
            f"The dev login is enabled in the '{settings.environment}' environment. "
            "It may only be enabled when VIGIL_ENV=dev."
        )
    if settings.environment == "prod":
        raise StartupRefused("VIGIL_ENV=prod is not supported in the MVP (synthetic data only; dev and test).")
