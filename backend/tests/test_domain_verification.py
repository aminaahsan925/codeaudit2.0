"""Domain verification endpoints: server-issued tokens, well-known URL only.

The app is built with `create_app(...)` and `get_db` is overridden with a
SQLite test session. The outbound fetch is faked by substituting the
SSRF-safe client in the verify module, so no test touches the network;
the fake records every requested URL, which is how the exact-URL
requirement is asserted.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.services.live.verify import VERIFICATION_PATH

SettingsFactory = Callable[..., Settings]

DOMAIN = "shop.example.com"
WELL_KNOWN_URL = f"https://{DOMAIN}{VERIFICATION_PATH}"


@pytest.fixture
def db_session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(settings_factory: SettingsFactory, db_session: Session, tmp_path: Path) -> TestClient:
    settings = settings_factory(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        artifact_dir=tmp_path / "artifacts",
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Substitute the SSRF-safe client with a fake serving canned bodies.

    `served` maps a URL to a (status, body) pair; anything unmapped is a
    404. `requested` records every URL the code fetched, in order.
    """
    served: dict[str, tuple[int, str]] = {}
    requested: list[str] = []

    class FakeSsrfClient:
        def __init__(self, allow_loopback: bool = False, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> FakeSsrfClient:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def get(self, url: str, **kwargs: Any) -> httpx.Response:
            requested.append(url)
            status, body = served.get(url, (404, "Not found"))
            return httpx.Response(status, text=body, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.services.live.verify.SsrfSafeClient", FakeSsrfClient)
    return SimpleNamespace(served=served, requested=requested)


def _auth(api_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_token}"}


def _issue_token(client: TestClient, domain: str = DOMAIN, **kwargs: Any) -> dict[str, Any]:
    response = client.post("/api/verification/token", json={"domain": domain}, **kwargs)
    assert response.status_code == 201
    return response.json()


# ------------------------------------------------------------------ token


def test_token_is_server_generated_and_random_per_request(client: TestClient) -> None:
    first = _issue_token(client)
    second = _issue_token(client)

    assert first["domain"] == DOMAIN
    assert first["token"]
    assert first["verification_url"] == WELL_KNOWN_URL
    assert second["token"]
    assert second["token"] != first["token"]


def test_token_domain_is_normalized(client: TestClient) -> None:
    body = _issue_token(client, domain="Shop.EXAMPLE.com.")

    assert body["domain"] == DOMAIN
    assert body["verification_url"] == WELL_KNOWN_URL


def test_new_token_replaces_old_token(client: TestClient, fake_http: SimpleNamespace) -> None:
    first = _issue_token(client)
    fake_http.served[WELL_KNOWN_URL] = (200, first["token"])
    assert (
        client.post("/api/verification/check", json={"domain": DOMAIN}).json()["verified"] is True
    )

    second = _issue_token(client)
    assert second["token"] != first["token"]

    # The old token no longer verifies once replaced.
    fake_http.served[WELL_KNOWN_URL] = (200, first["token"])
    assert (
        client.post("/api/verification/check", json={"domain": DOMAIN}).json()["verified"] is False
    )

    fake_http.served[WELL_KNOWN_URL] = (200, second["token"])
    assert (
        client.post("/api/verification/check", json={"domain": DOMAIN}).json()["verified"] is True
    )


@pytest.mark.parametrize("domain", ["https://shop.example.com", "not a domain", "exa_mple.com", ""])
def test_token_rejects_invalid_domain(client: TestClient, domain: str) -> None:
    response = client.post("/api/verification/token", json={"domain": domain})

    assert response.status_code in (400, 422)


@pytest.mark.parametrize("domain", ["localhost", "127.0.0.1", "shop.local"])
def test_token_rejects_local_domain(client: TestClient, domain: str) -> None:
    response = client.post("/api/verification/token", json={"domain": domain})

    assert response.status_code == 400
    assert "Local addresses" in response.json()["error"]["message"]


# ------------------------------------------------------------------ check


def test_check_succeeds_at_exact_well_known_url(
    client: TestClient, fake_http: SimpleNamespace
) -> None:
    issued = _issue_token(client)
    fake_http.served[WELL_KNOWN_URL] = (200, issued["token"])

    response = client.post("/api/verification/check", json={"domain": DOMAIN})

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["domain"] == DOMAIN
    assert body["verified_at"] is not None
    assert fake_http.requested == [WELL_KNOWN_URL]


def test_check_wrong_token_fails(client: TestClient, fake_http: SimpleNamespace) -> None:
    _issue_token(client)
    fake_http.served[WELL_KNOWN_URL] = (200, "some-other-token")

    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False
    assert body["verified_at"] is None


def test_check_missing_file_fails(client: TestClient, fake_http: SimpleNamespace) -> None:
    _issue_token(client)

    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False
    assert fake_http.requested == [WELL_KNOWN_URL]


def test_check_token_at_other_path_fails(client: TestClient, fake_http: SimpleNamespace) -> None:
    issued = _issue_token(client)
    fake_http.served[f"https://{DOMAIN}/verification.txt"] = (200, issued["token"])
    fake_http.served[f"https://{DOMAIN}/"] = (200, issued["token"])

    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False
    # Only the well-known URL is ever fetched.
    assert fake_http.requested == [WELL_KNOWN_URL]


def test_check_meta_tag_does_not_verify(client: TestClient, fake_http: SimpleNamespace) -> None:
    issued = _issue_token(client)
    fake_http.served[f"https://{DOMAIN}/"] = (
        200,
        f'<html><head><meta name="launchaudit-verification" '
        f'content="{issued["token"]}"></head></html>',
    )

    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False
    assert fake_http.requested == [WELL_KNOWN_URL]


def test_check_without_issued_token_fails(client: TestClient) -> None:
    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False
    assert body["verified_at"] is None


def test_failed_check_clears_verified_mark(client: TestClient, fake_http: SimpleNamespace) -> None:
    issued = _issue_token(client)
    fake_http.served[WELL_KNOWN_URL] = (200, issued["token"])
    assert (
        client.post("/api/verification/check", json={"domain": DOMAIN}).json()["verified"] is True
    )

    fake_http.served[WELL_KNOWN_URL] = (200, "some-other-token")
    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False
    assert body["verified_at"] is None


def test_check_rejects_invalid_domain(client: TestClient) -> None:
    response = client.post("/api/verification/check", json={"domain": "https://shop.example.com"})

    assert response.status_code == 400


# -------------------------------------------------------------- scoping


def test_guest_token_is_not_usable_by_signed_in_owner(
    client: TestClient, fake_http: SimpleNamespace, api_token: str
) -> None:
    issued = _issue_token(client)
    fake_http.served[WELL_KNOWN_URL] = (200, issued["token"])

    body = client.post(
        "/api/verification/check",
        json={"domain": DOMAIN},
        headers=_auth(api_token),
    ).json()

    assert body["verified"] is False


def test_owner_token_is_not_usable_by_guest(
    client: TestClient, fake_http: SimpleNamespace, api_token: str
) -> None:
    issued = _issue_token(client, headers=_auth(api_token))
    fake_http.served[WELL_KNOWN_URL] = (200, issued["token"])

    body = client.post("/api/verification/check", json={"domain": DOMAIN}).json()

    assert body["verified"] is False


def test_owner_token_verifies_for_its_owner(
    client: TestClient, fake_http: SimpleNamespace, api_token: str
) -> None:
    issued = _issue_token(client, headers=_auth(api_token))
    fake_http.served[WELL_KNOWN_URL] = (200, issued["token"])

    body = client.post(
        "/api/verification/check",
        json={"domain": DOMAIN},
        headers=_auth(api_token),
    ).json()

    assert body["verified"] is True
