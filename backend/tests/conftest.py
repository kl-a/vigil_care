from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {"environment": "test", "dev_login_enabled": False}
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.fixture
def client_factory() -> Callable[..., TestClient]:
    def build(database_ok: bool = True, **overrides: object) -> TestClient:
        app = create_app(make_settings(**overrides), database_check=lambda: database_ok)
        return TestClient(app)

    return build
