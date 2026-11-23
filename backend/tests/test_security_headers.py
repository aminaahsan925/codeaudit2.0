from collections.abc import Callable
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.security import CONTENT_SECURITY_POLICY, HSTS_VALUE

MakeClient = Callable[..., TestClient]

PRODUCTION: dict[str, Any] = {
    "environment": "production",
    "cors_origins": ["https://app.example.com"],
}


def boom() -> None:
    raise RuntimeError("boom")


async def read_body(request: Request) -> dict[str, int]:
    return {"size": len(await request.body())}


ROUTES: list[tuple[str, list[str], Callable[..., Any]]] = [
    ("/api/_test/boom", ["GET"], boom),
    ("/api/_test/body", ["POST"], read_body),
]


def test_base_security_headers_on_json_response(client: TestClient) -> None:
    headers = client.get("/api/health").headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert headers["cross-origin-opener-policy"] == "same-origin"


def test_csp_on_json_responses(client: TestClient) -> None:
    csp = client.get("/api/health").headers["content-security-policy"]

    assert csp == CONTENT_SECURITY_POLICY
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_api_responses_are_not_cacheable(client: TestClient) -> None:
    assert client.get("/api/health").headers["cache-control"] == "no-store"
    assert client.get("/api/auth/me").headers["cache-control"] == "no-store"


def test_csp_is_skipped_only_for_api_docs_in_development(client: TestClient) -> None:
    docs = client.get("/api/docs")

    assert docs.status_code == 200
    assert "content-security-policy" not in docs.headers
    assert docs.headers["x-content-type-options"] == "nosniff"
    assert docs.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in client.get("/api/openapi.json").headers
    assert "content-security-policy" in client.get("/api/health").headers
    assert "content-security-policy" in client.get("/api/docs/other").headers


def test_hsts_absent_in_development(client: TestClient) -> None:
    assert "strict-transport-security" not in client.get("/api/health").headers


def test_hsts_present_in_production(make_client: MakeClient) -> None:
    response = make_client(**PRODUCTION).get("/api/health")

    assert response.headers["strict-transport-security"] == HSTS_VALUE


def test_production_sends_csp_on_the_docs_path(make_client: MakeClient) -> None:
    response = make_client(**PRODUCTION).get("/api/docs")

    assert response.status_code == 404
    assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY


def test_headers_on_404(client: TestClient) -> None:
    response = client.get("/api/missing")

    assert response.status_code == 404
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["cache-control"] == "no-store"


def test_headers_on_413(make_client: MakeClient) -> None:
    client = make_client(routes=ROUTES, max_request_bytes=10)
    response = client.post("/api/_test/body", content=b"x" * 50)

    assert response.status_code == 413
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("production", [False, True])
def test_headers_on_500(make_client: MakeClient, production: bool) -> None:
    overrides = PRODUCTION if production else {}
    response = make_client(routes=ROUTES, **overrides).get("/api/_test/boom")

    assert response.status_code == 500
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"]
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert response.headers["cache-control"] == "no-store"
    assert ("strict-transport-security" in response.headers) is production
