import base64
import pytest
from pydantic import ValidationError

from app.core.config import DEV_ENCRYPTION_KEY, DEV_SESSION_SECRET, StartupRefused, keystore
from app.core.crypto import FieldCipher
from app.main import create_app
from tests.conftest import make_settings


def test_dev_environment_may_enable_the_dev_login() -> None:
    app = create_app(make_settings(environment="dev", dev_login_enabled=True), database_check=lambda: True)
    assert app.title == "Vigil"


def test_test_environment_refuses_to_start_with_the_dev_login_enabled() -> None:
    with pytest.raises(StartupRefused, match="dev login"):
        create_app(make_settings(environment="test", dev_login_enabled=True), database_check=lambda: True)


def test_prod_is_recognised_but_refuses_to_start_in_the_mvp() -> None:
    with pytest.raises(StartupRefused, match="prod"):
        create_app(make_settings(environment="prod"), database_check=lambda: True)


def test_prod_with_the_dev_login_enabled_is_refused() -> None:
    with pytest.raises(StartupRefused):
        create_app(make_settings(environment="prod", dev_login_enabled=True), database_check=lambda: True)


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(environment="staging")


def test_environment_is_read_from_vigil_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("VIGIL_ENV", "test")  # not the default, so this can't pass by accident
    monkeypatch.setenv("VIGIL_DEV_LOGIN_ENABLED", "true")
    settings = Settings()
    assert settings.environment == "test"
    assert settings.dev_login_enabled is True


def test_the_guard_fires_from_real_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIGIL_ENV", "test")
    monkeypatch.setenv("VIGIL_DEV_LOGIN_ENABLED", "true")
    with pytest.raises(StartupRefused):
        create_app(database_check=lambda: True)


def test_the_dev_session_secret_is_refused_outside_dev() -> None:
    with pytest.raises(StartupRefused, match="session secret"):
        create_app(make_settings(environment="test", session_secret=DEV_SESSION_SECRET), database_check=lambda: True)


def test_a_short_session_secret_is_refused_outside_dev() -> None:
    with pytest.raises(StartupRefused, match="session secret"):
        create_app(make_settings(environment="test", session_secret="too-short"), database_check=lambda: True)


def test_an_empty_session_secret_falls_back_to_the_dev_default() -> None:
    assert make_settings(environment="dev", session_secret="").session_secret == DEV_SESSION_SECRET


def test_a_real_session_secret_is_accepted_in_test() -> None:
    app = create_app(make_settings(environment="test", session_secret="s" * 48), database_check=lambda: True)
    assert app.title == "Vigil"


def test_the_dev_encryption_key_is_refused_outside_dev() -> None:
    with pytest.raises(StartupRefused, match="encryption key"):
        create_app(make_settings(environment="test", encryption_key=DEV_ENCRYPTION_KEY), database_check=lambda: True)


def test_an_encryption_key_that_isnt_256_bits_is_refused() -> None:
    with pytest.raises(StartupRefused, match="encryption key"):
        create_app(make_settings(encryption_key="dG9vIHNob3J0"), database_check=lambda: True)


def test_values_sealed_before_a_rotation_open_with_the_previous_key_configured() -> None:
    old = base64.b64encode(bytes([1] * 32)).decode()
    new = base64.b64encode(bytes([2] * 32)).decode()
    sealed = FieldCipher(keystore(make_settings(encryption_key=old))).encrypt("0491 570 156", context="c")
    rotated = FieldCipher(keystore(make_settings(encryption_key=new, previous_encryption_keys=f" {old} ")))
    assert rotated.decrypt(sealed, context="c") == "0491 570 156"
