from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient

MakeClient = Callable[..., TestClient]
ALLOWED = "http://localhost:3000"
EVIL = "https://evil.example.com"


def preflight(
    client: TestClient, origin: str, request_headers: str = "Authorization"
) -> httpx.Response:
    return client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": request_headers,
        },
    )


def test_allowed_origin_preflight_succeeds(client: TestClient) -> None:
    response = preflight(client, ALLOWED)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]


def test_preflight_allows_credentials(client: TestClient) -> None:
    """The session cookie travels cross-origin, so allowed origins get
    Access-Control-Allow-Credentials."""
    response = preflight(client, ALLOWED)

    assert response.headers["access-control-allow-credentials"] == "true"


def test_actual_request_from_allowed_origin_has_cors_header(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": ALLOWED})

    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"


def test_disallowed_origin_preflight_uses_error_format(client: TestClient) -> None:
    response = preflight(client, EVIL)

    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "bad_request", "message": "CORS preflight request was rejected."}
    }
    assert "access-control-allow-origin" not in response.headers


def test_disallowed_header_preflight_uses_error_format(client: TestClient) -> None:
    response = preflight(client, ALLOWED, request_headers="X-Evil")

    assert response.status_code == 400
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message"}


def test_disallowed_method_preflight_is_rejected(client: TestClient) -> None:
    response = client.options(
        "/api/health",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "TRACE"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_disallowed_origin_actual_request_gets_no_cors_header(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": EVIL})

    assert "access-control-allow-origin" not in response.headers


def test_rejected_preflight_still_has_security_headers(client: TestClient) -> None:
    response = preflight(client, EVIL)

    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in response.headers


def test_configured_origins_are_honoured(make_client: MakeClient) -> None:
    client = make_client(cors_origins=["https://app.example.com"])

    assert preflight(client, "https://app.example.com").status_code == 200
    assert preflight(client, ALLOWED).status_code == 400
