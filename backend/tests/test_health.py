from collections.abc import Callable

from fastapi.testclient import TestClient


def test_health_returns_ok_and_version(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


def test_health_needs_no_authentication(client: TestClient) -> None:
    assert "authorization" not in client.headers
    assert client.get("/api/health").status_code == 200


def test_health_ignores_a_bad_token(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Authorization": "Bearer nonsense"})

    assert response.status_code == 200


def test_health_reports_configured_version(make_client: Callable[..., TestClient]) -> None:
    with make_client(app_version="9.9.9") as test_client:
        assert test_client.get("/api/health").json() == {"status": "ok", "version": "9.9.9"}


def test_health_rejects_post(client: TestClient) -> None:
    assert client.post("/api/health").status_code == 405
