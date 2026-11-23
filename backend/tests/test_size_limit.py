from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

MakeClient = Callable[..., TestClient]
LIMIT = 100


async def read_body(request: Request) -> dict[str, int]:
    return {"size": len(await request.body())}


ROUTES: list[tuple[str, list[str], Callable[..., Any]]] = [
    ("/api/_test/body", ["POST"], read_body),
]


@pytest.fixture
def small_client(make_client: MakeClient) -> TestClient:
    return make_client(routes=ROUTES, max_request_bytes=LIMIT)


def chunks(total: int, size: int = 10) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        piece = min(size, total - sent)
        yield b"x" * piece
        sent += piece


def assert_payload_too_large(response: Any) -> None:
    assert response.status_code == 413
    assert response.json() == {
        "error": {"code": "payload_too_large", "message": "Request body is too large."}
    }


def test_content_length_over_limit_is_413(small_client: TestClient) -> None:
    response = small_client.post("/api/_test/body", content=b"x" * (LIMIT + 1))

    assert_payload_too_large(response)


def test_body_exactly_at_limit_passes(small_client: TestClient) -> None:
    response = small_client.post("/api/_test/body", content=b"x" * LIMIT)

    assert response.status_code == 200
    assert response.json() == {"size": LIMIT}


def test_body_just_under_limit_passes(small_client: TestClient) -> None:
    response = small_client.post("/api/_test/body", content=b"x" * (LIMIT - 1))

    assert response.status_code == 200
    assert response.json() == {"size": LIMIT - 1}


def test_streamed_body_over_limit_without_content_length_is_413(small_client: TestClient) -> None:
    request = small_client.build_request("POST", "/api/_test/body", content=chunks(LIMIT * 5))
    assert "content-length" not in request.headers
    assert request.headers["transfer-encoding"] == "chunked"

    assert_payload_too_large(small_client.send(request))


def test_streamed_body_under_limit_passes(small_client: TestClient) -> None:
    response = small_client.post("/api/_test/body", content=chunks(LIMIT - 20))

    assert response.status_code == 200
    assert response.json() == {"size": LIMIT - 20}


def test_default_limit_is_one_megabyte(client: TestClient) -> None:
    response = client.post("/api/health", content=b"x" * (1_048_576 + 1))

    assert_payload_too_large(response)


def test_get_requests_are_unaffected(small_client: TestClient) -> None:
    assert small_client.get("/api/health").status_code == 200
