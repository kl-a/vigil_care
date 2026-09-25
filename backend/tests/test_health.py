from collections.abc import Callable

from fastapi.testclient import TestClient


def test_health_is_green_when_the_database_is_reachable(client_factory: Callable[..., TestClient]) -> None:
    response = client_factory(database_ok=True).get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["database"] == "ok"


def test_health_reports_degraded_when_the_database_is_unreachable(client_factory: Callable[..., TestClient]) -> None:
    response = client_factory(database_ok=False).get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unreachable"


def test_health_reports_the_vlm_worker_as_not_configured_without_a_url(
    client_factory: Callable[..., TestClient],
) -> None:
    assert client_factory().get("/health").json()["vlm_worker"] == "not_configured"


def test_health_reports_the_vlm_worker_as_configured_when_a_url_is_set(
    client_factory: Callable[..., TestClient],
) -> None:
    client = client_factory(vlm_worker_url="http://vlm.local:8080")
    assert client.get("/health").json()["vlm_worker"] == "configured"


def test_interactive_api_docs_and_schema_are_reachable(client_factory: Callable[..., TestClient]) -> None:
    client = client_factory()
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/health" in schema["paths"]
