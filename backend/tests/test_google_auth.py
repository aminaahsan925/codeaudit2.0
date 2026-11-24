"""Google sign-in, demo sign-in and session auth API tests.

Google is mocked with httpx.MockTransport; no test touches Google. The app
uses a SQLite test database via a get_db override.
"""

from __future__ import annotations

import io
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_http_client
from app.api.routers import runs as runs_router
from app.core.config import Settings
from app.core.security import issue_oauth_state, issue_session_token, verify_session_token
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.repositories.users import UserRepository

SettingsFactory = Callable[..., Settings]
MakeClient = Callable[..., TestClient]

TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef0123456789"  # noqa: S105
GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "test-google-client-secret"  # noqa: S105
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"
GOOGLE_SUB = "google-sub-12345"
GOOGLE_EMAIL = "amina@example.com"


def _tokeninfo_claims(**overrides: Any) -> dict[str, Any]:
    claims: dict[str, Any] = {
        "aud": GOOGLE_CLIENT_ID,
        "sub": GOOGLE_SUB,
        "email": GOOGLE_EMAIL,
        "email_verified": "true",
        "name": "Amina Ahsan",
        "picture": "https://example.com/pic.jpg",
        "exp": str(int(time.time()) + 3600),
    }
    claims.update(overrides)
    return claims


def _google_success_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if urlparse(url).path == "/token":
        return httpx.Response(
            200,
            json={
                "id_token": "test-id-token",
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )
    if urlparse(url).path == "/tokeninfo":
        return httpx.Response(200, json=_tokeninfo_claims())
    raise AssertionError(f"unexpected Google request to {url}")


@pytest.fixture
def db_session(tmp_path: Path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as session:
        yield session
    engine.dispose()


@pytest.fixture
def make_auth_client(
    settings_factory: SettingsFactory, db_session: Session, tmp_path: Path
) -> MakeClient:
    """Build a client for an app with Google + sessions configured by default.

    Pass `google_handler=` to answer Google differently, and any settings
    override (e.g. `google_client_id=None`) to change the configuration.
    """

    def build(
        google_handler: Callable[[httpx.Request], httpx.Response] = _google_success_handler,
        **overrides: Any,
    ) -> TestClient:
        values: dict[str, Any] = {
            "google_client_id": GOOGLE_CLIENT_ID,
            "google_client_secret": GOOGLE_CLIENT_SECRET,
            "google_redirect_uri": GOOGLE_REDIRECT_URI,
            "session_secret": TEST_SESSION_SECRET,
            "artifact_dir": tmp_path / "artifacts",
        }
        values.update(overrides)
        app = create_app(settings_factory(**values))
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_http_client] = lambda: httpx.Client(
            transport=httpx.MockTransport(google_handler)
        )
        return TestClient(app, raise_server_exceptions=False)

    return build


@pytest.fixture
def auth_client(make_auth_client: MakeClient) -> TestClient:
    return make_auth_client()


def _valid_state() -> str:
    return issue_oauth_state(TEST_SESSION_SECRET)


def _callback_url(state: str | None = None, code: str = "test-code") -> str:
    state = _valid_state() if state is None else state
    return f"/api/auth/google/callback?code={code}&state={state}"


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("app.py", "print('hello')\n")
    return buffer.getvalue()


# ---------------------------------------------------------------- providers


def test_providers_google_when_configured(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/providers")

    assert response.status_code == 200
    assert response.json() == {"google": True, "demo": False}


def test_providers_demo_when_google_unconfigured(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_client_id=None)

    response = client.get("/api/auth/providers")

    assert response.status_code == 200
    assert response.json() == {"google": False, "demo": True}


def test_providers_none_without_session_secret(make_auth_client: MakeClient) -> None:
    client = make_auth_client(session_secret=None)

    response = client.get("/api/auth/providers")

    assert response.status_code == 200
    assert response.json() == {"google": False, "demo": False}


# -------------------------------------------------------------- google login


def test_google_login_redirects_to_google(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/google/login", follow_redirects=False)

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert location.netloc == "accounts.google.com"
    assert location.path == "/o/oauth2/v2/auth"
    query = parse_qs(location.query)
    assert query["client_id"] == [GOOGLE_CLIENT_ID]
    assert query["redirect_uri"] == [GOOGLE_REDIRECT_URI]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["state"] != [""]


def test_google_login_404_when_unconfigured(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_client_id=None)

    response = client.get("/api/auth/google/login", follow_redirects=False)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_google_login_404_without_session_secret(make_auth_client: MakeClient) -> None:
    client = make_auth_client(session_secret=None)

    response = client.get("/api/auth/google/login", follow_redirects=False)

    assert response.status_code == 404


# ------------------------------------------------------------ google callback


def test_callback_creates_user_and_redirects_with_token(
    auth_client: TestClient, db_session: Session
) -> None:
    response = auth_client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert location.netloc == "localhost:3000"
    assert location.path == "/auth/callback"
    token = parse_qs(location.query)["token"][0]
    claims = verify_session_token(token, TEST_SESSION_SECRET)
    assert claims is not None
    assert claims.email == GOOGLE_EMAIL
    assert claims.demo is False

    user = UserRepository(db_session).get_by_google_sub(GOOGLE_SUB)
    assert user is not None
    assert user.id == claims.user_id
    assert user.email == GOOGLE_EMAIL
    assert user.name == "Amina Ahsan"
    assert user.picture_url == "https://example.com/pic.jpg"
    assert user.is_demo is False


def test_callback_twice_updates_profile_without_duplicating(
    auth_client: TestClient, db_session: Session
) -> None:
    assert auth_client.get(_callback_url(), follow_redirects=False).status_code == 302

    def renamed_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if urlparse(url).path == "/token":
            return httpx.Response(200, json={"id_token": "test-id-token"})
        return httpx.Response(200, json=_tokeninfo_claims(name="Amina Renamed", picture=None))

    auth_client.app.dependency_overrides[get_http_client] = lambda: httpx.Client(
        transport=httpx.MockTransport(renamed_handler)
    )
    response = auth_client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 302
    users = UserRepository(db_session)
    assert users.get_by_google_sub(GOOGLE_SUB) is not None
    assert users.get_by_email(GOOGLE_EMAIL) is not None
    assert users.get_by_google_sub(GOOGLE_SUB).name == "Amina Renamed"


def test_callback_bad_state_is_400(auth_client: TestClient) -> None:
    response = auth_client.get(_callback_url(state="not-a-state"), follow_redirects=False)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_callback_missing_code_is_400(auth_client: TestClient) -> None:
    response = auth_client.get(
        f"/api/auth/google/callback?state={_valid_state()}", follow_redirects=False
    )

    assert response.status_code == 400


def test_callback_google_error_param_is_400(auth_client: TestClient) -> None:
    response = auth_client.get(
        f"/api/auth/google/callback?error=access_denied&state={_valid_state()}",
        follow_redirects=False,
    )

    assert response.status_code == 400


def test_callback_exchange_failure_is_400(make_auth_client: MakeClient) -> None:
    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    client = make_auth_client(google_handler=failing_handler)

    response = client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 400
    assert "invalid_grant" not in response.text


def test_callback_wrong_audience_is_400(make_auth_client: MakeClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if urlparse(str(request.url)).path == "/token":
            return httpx.Response(200, json={"id_token": "test-id-token"})
        return httpx.Response(200, json=_tokeninfo_claims(aud="another-app"))

    client = make_auth_client(google_handler=handler)

    response = client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 400


def test_callback_expired_id_token_is_400(make_auth_client: MakeClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if urlparse(str(request.url)).path == "/token":
            return httpx.Response(200, json={"id_token": "test-id-token"})
        return httpx.Response(200, json=_tokeninfo_claims(exp=str(int(time.time()) - 10)))

    client = make_auth_client(google_handler=handler)

    response = client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 400


def test_callback_unverified_email_is_400(make_auth_client: MakeClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if urlparse(str(request.url)).path == "/token":
            return httpx.Response(200, json={"id_token": "test-id-token"})
        return httpx.Response(200, json=_tokeninfo_claims(email_verified="false"))

    client = make_auth_client(google_handler=handler)

    response = client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 400


# --------------------------------------------------------------- demo login


def test_demo_login_issues_demo_session(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_client_id=None)

    response = client.post("/api/auth/demo-login")

    assert response.status_code == 200
    body = response.json()
    assert body["demo"] is True
    assert body["user"]["email"] == "demo@launchaudit.local"
    assert body["user"]["name"] == "Demo User"
    assert body["user"]["demo"] is True
    claims = verify_session_token(body["token"], TEST_SESSION_SECRET)
    assert claims is not None
    assert claims.demo is True
    assert str(claims.user_id) == body["user"]["id"]


def test_demo_login_twice_reuses_the_same_user(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_client_id=None)

    first = client.post("/api/auth/demo-login").json()
    second = client.post("/api/auth/demo-login").json()

    assert first["user"]["id"] == second["user"]["id"]


def test_demo_login_disabled_when_google_configured(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/demo-login")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_demo_login_disabled_without_session_secret(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_client_id=None, session_secret=None)

    response = client.post("/api/auth/demo-login")

    assert response.status_code == 404


# -------------------------------------------------------------------- /me


def _demo_token(make_auth_client: MakeClient) -> str:
    client = make_auth_client(google_client_id=None)
    return str(client.post("/api/auth/demo-login").json()["token"])


def test_me_with_session_token_returns_user(
    make_auth_client: MakeClient, auth_client: TestClient
) -> None:
    token = _demo_token(make_auth_client)

    response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "demo@launchaudit.local"
    assert body["email"] == "demo@launchaudit.local"
    assert body["name"] == "Demo User"
    assert body["demo"] is True


def test_me_with_expired_session_is_401(
    auth_client: TestClient,
) -> None:
    token = issue_session_token(
        TEST_SESSION_SECRET,
        user_id=UUID(int=1),
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
        expires_in_days=-1,
    )

    response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_me_anonymous_is_401(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_session_token_works_in_production(
    make_auth_client: MakeClient, settings_factory: Callable[..., Settings]
) -> None:
    token = _demo_token(make_auth_client)
    production = make_auth_client(
        environment="production",
        api_auth_token=None,
        google_client_id=None,
        cors_origins=["https://app.example.com"],
    )
    assert settings_factory(environment="production").is_production

    response = production.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "demo@launchaudit.local"


def test_logout_returns_signed_out(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"signed_out": True}


# ----------------------------------------------------------- runs linkage


def test_run_created_with_session_is_owned_not_guest(
    make_auth_client: MakeClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _demo_token(make_auth_client)
    client = make_auth_client(google_client_id=None)
    monkeypatch.setattr(runs_router, "execute_run", lambda *args, **kwargs: None)

    response = client.post(
        "/api/runs",
        data={"project_name": "Demo shop"},
        files={"zip_file": ("app.zip", _zip_bytes(), "application/zip")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_guest"] is False


def test_run_created_without_token_is_guest(
    make_auth_client: MakeClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = make_auth_client(google_client_id=None)
    monkeypatch.setattr(runs_router, "execute_run", lambda *args, **kwargs: None)

    response = client.post(
        "/api/runs",
        data={"project_name": "Demo shop"},
        files={"zip_file": ("app.zip", _zip_bytes(), "application/zip")},
    )

    assert response.status_code == 201
    assert response.json()["is_guest"] is True
