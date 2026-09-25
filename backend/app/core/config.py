from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.seams.keys import Keystore, LocalKeystore

Environment = Literal["dev", "test", "prod"]

# The repo-root .env, whatever directory a command runs from (make runs backend commands from backend/).
# A local .env, if any, wins. In Docker there is no file: settings come from the environment.
ENV_FILES = (Path(__file__).resolve().parents[3] / ".env", Path(".env"))

# Signs dev session cookies. Refused outside dev, so a real secret must be set there.
DEV_SESSION_SECRET = "dev-only-session-secret-never-use-outside-dev"
MIN_SESSION_SECRET_LENGTH = 32
# Encrypts Patient Identity in dev (synthetic data only). Refused outside dev, so a real key must be set there.
DEV_ENCRYPTION_KEY = "ZGV2LW9ubHktZW5jcnlwdGlvbi1rZXktbmV2ZXItdXM="


class StartupRefused(RuntimeError):
    """Raised when the configuration must never be allowed to run."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIGIL_", env_file=ENV_FILES, extra="ignore")

    # Read from VIGIL_ENV (the documented name), not the prefix-derived VIGIL_ENVIRONMENT.
    environment: Environment = Field(default="dev", validation_alias=AliasChoices("VIGIL_ENV", "environment"))
    dev_login_enabled: bool = False
    database_url: str = "postgresql://vigil_app:vigil_app_dev@localhost:5432/vigil"
    vlm_worker_url: str | None = None
    session_secret: str = DEV_SESSION_SECRET
    # Base64 of a random 32-byte key (e.g. `openssl rand -base64 32`), behind the key interface (ADR 0003).
    encryption_key: str = DEV_ENCRYPTION_KEY
    # After a rotation: the older keys, comma-separated, so values they sealed still open.
    previous_encryption_keys: str = ""

    @field_validator("session_secret")
    @classmethod
    def _unset_means_dev_default(cls, value: str) -> str:
        # Docker Compose passes an empty string when VIGIL_SESSION_SECRET isn't set.
        return value or DEV_SESSION_SECRET

    @field_validator("encryption_key")
    @classmethod
    def _unset_key_means_dev_default(cls, value: str) -> str:
        return value or DEV_ENCRYPTION_KEY


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
    if settings.environment != "dev" and settings.encryption_key == DEV_ENCRYPTION_KEY:
        raise StartupRefused(
            f"The encryption key in the '{settings.environment}' environment is the dev default. "
            "Set VIGIL_ENCRYPTION_KEY to a random 32-byte key, base64-encoded (openssl rand -base64 32)."
        )
    try:
        keystore(settings)
    except ValueError as error:
        raise StartupRefused(f"The encryption key (VIGIL_ENCRYPTION_KEY) isn't usable: {error}") from None
    if settings.environment == "prod":
        raise StartupRefused("VIGIL_ENV=prod is not supported in the MVP (synthetic data only; dev and test).")


def keystore(settings: Settings) -> Keystore:
    """The key interface's implementation for these settings: the local keystore until Key Vault (ADR 0003)."""
    previous = [secret.strip() for secret in settings.previous_encryption_keys.split(",") if secret.strip()]
    return LocalKeystore.from_secrets(settings.encryption_key, previous=previous)
