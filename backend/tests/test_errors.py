from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, ForbiddenError, NotFoundError, UnauthorizedError

MakeClient = Callable[..., TestClient]

SENTINEL = "supersecret-value-do-not-echo"
INTERNAL_DETAIL = "db password=hunter2 at /srv/app/internal.py"
JSON_HEADERS = {"content-type": "application/json"}


class Payload(BaseModel):
    name: str
    count: int


def echo(payload: Payload) -> dict[str, str]:
    return {"name": payload.name}


def boom() -> None:
    raise RuntimeError(INTERNAL_DETAIL)


def raise_app_error() -> None:
    raise AppError("Custom safe message.")


def raise_forbidden() -> None:
    raise ForbiddenError


def raise_not_found() -> None:
    raise NotFoundError("Thing not found.")


def raise_unauthorized() -> None:
    raise UnauthorizedError


ROUTES: list[tuple[str, list[str], Callable[..., Any]]] = [
    ("/api/_test/echo", ["POST"], echo),
    ("/api/_test/boom", ["GET"], boom),
    ("/api/_test/app-error", ["GET"], raise_app_error),
    ("/api/_test/forbidden", ["GET"], raise_forbidden),
    ("/api/_test/missing", ["GET"], raise_not_found),
    ("/api/_test/unauthorized", ["GET"], raise_unauthorized),
]


@pytest.fixture
def err_client(make_client: MakeClient) -> TestClient:
    return make_client(routes=ROUTES)


def assert_envelope(body: dict[str, Any], code: str) -> None:
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]


def test_unknown_route_is_404_not_found(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert_envelope(response.json(), "not_found")
    assert response.json()["error"]["message"] == "Resource not found."


def test_wrong_method_is_405_with_allow_header(client: TestClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    assert_envelope(response.json(), "method_not_allowed")
    assert "GET" in response.headers["allow"]


def test_validation_error_is_422_and_names_the_field(err_client: TestClient) -> None:
    response = err_client.post("/api/_test/echo", json={"name": "ok", "count": SENTINEL})

    assert response.status_code == 422
    assert_envelope(response.json(), "validation_error")
    assert "count" in response.json()["error"]["message"]


def test_validation_error_does_not_echo_submitted_values(err_client: TestClient) -> None:
    response = err_client.post("/api/_test/echo", json={"name": 123456, "count": SENTINEL})

    assert response.status_code == 422
    assert SENTINEL not in response.text
    assert "123456" not in response.text


def test_validation_error_does_not_echo_values_of_wrong_type_body(err_client: TestClient) -> None:
    response = err_client.post("/api/_test/echo", json=[SENTINEL])

    assert response.status_code == 422
    assert SENTINEL not in response.text


def test_validation_error_for_missing_fields_names_them(err_client: TestClient) -> None:
    response = err_client.post("/api/_test/echo", json={})

    assert response.status_code == 422
    assert_envelope(response.json(), "validation_error")
    message = response.json()["error"]["message"]
    assert "name" in message
    assert "count" in message


def test_malformed_json_is_400_bad_request(err_client: TestClient) -> None:
    response = err_client.post(
        "/api/_test/echo", content='{"name": "a", "count": ', headers=JSON_HEADERS
    )

    assert response.status_code == 400
    assert_envelope(response.json(), "bad_request")


def test_malformed_json_does_not_echo_the_body(err_client: TestClient) -> None:
    response = err_client.post(
        "/api/_test/echo", content=f'{{"x": {SENTINEL}', headers=JSON_HEADERS
    )

    assert response.status_code == 400
    assert SENTINEL not in response.text


def test_unhandled_exception_is_generic_500(err_client: TestClient) -> None:
    response = err_client.get("/api/_test/boom")

    assert response.status_code == 500
    assert_envelope(response.json(), "internal_error")
    assert response.json()["error"]["message"] == "An unexpected error occurred."


def test_500_body_has_no_traceback_or_internal_detail(err_client: TestClient) -> None:
    response = err_client.get("/api/_test/boom")

    for leaked in ("Traceback", "RuntimeError", "hunter2", "internal.py", "File "):
        assert leaked not in response.text


def test_500_is_logged_server_side(
    err_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("ERROR"):
        err_client.get("/api/_test/boom")

    assert any(record.exc_info for record in caplog.records)


def test_app_error_uses_its_safe_message(err_client: TestClient) -> None:
    response = err_client.get("/api/_test/app-error")

    assert response.status_code == 400
    assert_envelope(response.json(), "bad_request")
    assert response.json()["error"]["message"] == "Custom safe message."


def test_forbidden_error_is_403(err_client: TestClient) -> None:
    response = err_client.get("/api/_test/forbidden")

    assert response.status_code == 403
    assert_envelope(response.json(), "forbidden")


def test_not_found_error_is_404_with_message(err_client: TestClient) -> None:
    response = err_client.get("/api/_test/missing")

    assert response.status_code == 404
    assert_envelope(response.json(), "not_found")
    assert response.json()["error"]["message"] == "Thing not found."


def test_unauthorized_error_sets_www_authenticate(err_client: TestClient) -> None:
    response = err_client.get("/api/_test/unauthorized")

    assert response.status_code == 401
    assert_envelope(response.json(), "unauthorized")
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "code"),
    [
        ("GET", "/api/nope", {}, "not_found"),
        ("DELETE", "/api/health", {}, "method_not_allowed"),
        ("GET", "/api/auth/me", {}, "unauthorized"),
        ("POST", "/api/_test/echo", {"json": {}}, "validation_error"),
        ("POST", "/api/_test/echo", {"content": "{", "headers": JSON_HEADERS}, "bad_request"),
        ("GET", "/api/_test/boom", {}, "internal_error"),
    ],
)
def test_every_error_body_has_exactly_the_envelope(
    err_client: TestClient, method: str, path: str, kwargs: dict[str, Any], code: str
) -> None:
    response = err_client.request(method, path, **kwargs)

    assert response.headers["content-type"].startswith("application/json")
    assert_envelope(response.json(), code)
