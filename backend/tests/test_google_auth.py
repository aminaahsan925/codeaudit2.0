"""Google sign-in, demo sign-in and session auth API tests.

Google is mocked with httpx.MockTransport; no test touches Google. The app
uses a SQLite test database via a get_db override. ID tokens are real
RS256-signed JWTs verified against a JWKS served by the mock, the way
Google's keys work.
"""

from __future__ import annotations

import base64
import io
import threading
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_http_client
from app.api.routers import runs as runs_router
from app.core.config import Settings
from app.core.security import issue_oauth_state, issue_session_token, verify_session_token
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.models.user import UserModel
from app.repositories.users import UserRepository
from app.services.auth.google import GoogleProfile
from app.services.auth.users import upsert_google_user

SettingsFactory = Callable[..., Settings]
MakeClient = Callable[..., TestClient]

TEST_SESSION_SECRET = "test-session-secret-0123456789abcdef0123456789"  # noqa: S105
GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "test-google-client-secret"  # noqa: S105
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"
GOOGLE_SUB = "google-sub-12345"
GOOGLE_EMAIL = "amina@example.com"


def _b64url(value: int) -> str:
    size = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks() -> dict[str, Any]:
    numbers = _PRIVATE_KEY.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url(numbers.n),
                "e": _b64url(numbers.e),
            }
        ]
    }


def _private_pem(key) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _id_token(key=_PRIVATE_KEY, kid: str = "test-key-1", **overrides: Any) -> str:
    claims: dict[str, Any] = {
        "iss": "https://accounts.google.com",
        "aud": GOOGLE_CLIENT_ID,
        "sub": GOOGLE_SUB,
        "email": GOOGLE_EMAIL,
        "email_verified": True,
        "name": "Amina Ahsan",
        "picture": "https://example.com/pic.jpg",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    claims.update(overrides)
    return jwt.encode(claims, _private_pem(key), algorithm="RS256", headers={"kid": kid})


def _google_handler(
    id_token: str | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    token = _id_token() if id_token is None else id_token

    def handler(request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        if path == "/token":
            return httpx.Response(
                200,
                json={
                    "id_token": token,
                    "access_token": "test-access-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        if path == "/oauth2/v3/certs":
            return httpx.Response(200, json=_jwks())
        raise AssertionError(f"unexpected Google request to {request.url!s}")

    return handler


def _google_success_handler(request: httpx.Request) -> httpx.Response:
    return _google_handler()(request)


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


def _session_cookie(response: httpx.Response) -> str:
    return str(response.cookies["launchaudit_session"])


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


def test_callback_creates_user_and_sets_session_cookie(
    auth_client: TestClient, db_session: Session
) -> None:
    response = auth_client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    assert location.netloc == "localhost:3000"
    assert location.path == "/auth/callback"
    assert not location.query, "the session token must not travel in the URL"
    assert "token" not in response.headers["location"]

    set_cookie = response.headers["set-cookie"]
    assert "launchaudit_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    token = _session_cookie(response)
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

    renamed = _google_handler(_id_token(name="Amina Renamed", picture=None))
    auth_client.app.dependency_overrides[get_http_client] = lambda: httpx.Client(
        transport=httpx.MockTransport(renamed)
    )
    response = auth_client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 302
    users = UserRepository(db_session)
    assert users.get_by_google_sub(GOOGLE_SUB) is not None
    assert users.get_by_email(GOOGLE_EMAIL) is not None
    assert users.get_by_google_sub(GOOGLE_SUB).name == "Amina Renamed"


def test_concurrent_upserts_for_a_new_user_create_one_row(tmp_path: Path) -> None:
    """Two sign-ins for the same new Google account racing each other must
    both succeed and leave exactly one user row behind."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'race.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    profile = GoogleProfile(sub="race-sub", email="race@example.com", name="Race", picture=None)
    barrier = threading.Barrier(2)
    results: list[Any] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait(timeout=10)
            with maker() as session:
                user = upsert_google_user(session, profile)
                session.commit()
                results.append(user.id)
        except BaseException as exc:  # collected and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert errors == []
    assert len(results) == 2
    assert results[0] == results[1]
    with maker() as session:
        rows = session.scalars(select(UserModel)).all()
        assert len(rows) == 1
        assert rows[0].google_sub == "race-sub"
    engine.dispose()


def _assert_sign_in_failed_redirect(response: httpx.Response) -> None:
    """A failed or cancelled callback sends the browser back to the
    frontend sign-in page with an error flag, never a JSON error page."""
    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:3000/sign-in?error=google_failed"
    assert "launchaudit_session" not in response.headers.get("set-cookie", "")


def test_callback_bad_state_redirects_to_sign_in(auth_client: TestClient) -> None:
    response = auth_client.get(_callback_url(state="not-a-state"), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)


def test_callback_missing_code_redirects_to_sign_in(auth_client: TestClient) -> None:
    response = auth_client.get(
        f"/api/auth/google/callback?state={_valid_state()}", follow_redirects=False
    )

    _assert_sign_in_failed_redirect(response)


def test_callback_google_error_param_redirects_to_sign_in(auth_client: TestClient) -> None:
    response = auth_client.get(
        f"/api/auth/google/callback?error=access_denied&state={_valid_state()}",
        follow_redirects=False,
    )

    _assert_sign_in_failed_redirect(response)


def test_callback_exchange_failure_redirects_to_sign_in(make_auth_client: MakeClient) -> None:
    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    client = make_auth_client(google_handler=failing_handler)

    response = client.get(_callback_url(), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)
    assert "invalid_grant" not in response.text


def test_callback_wrong_audience_redirects_to_sign_in(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_handler=_google_handler(_id_token(aud="another-app")))

    response = client.get(_callback_url(), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)


def test_callback_expired_id_token_redirects_to_sign_in(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_handler=_google_handler(_id_token(exp=int(time.time()) - 10)))

    response = client.get(_callback_url(), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)


def test_callback_unverified_email_redirects_to_sign_in(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_handler=_google_handler(_id_token(email_verified=False)))

    response = client.get(_callback_url(), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)


def test_callback_unknown_signing_key_redirects_to_sign_in(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_handler=_google_handler(_id_token(kid="rotated-away-key")))

    response = client.get(_callback_url(), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)


def test_callback_wrong_signature_redirects_to_sign_in(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_handler=_google_handler(_id_token(key=_OTHER_KEY)))

    response = client.get(_callback_url(), follow_redirects=False)

    _assert_sign_in_failed_redirect(response)


def test_callback_production_cookie_is_secure_and_cross_site(
    make_auth_client: MakeClient,
) -> None:
    client = make_auth_client(
        environment="production",
        api_auth_token=None,
        cors_origins=["https://app.example.com"],
        frontend_url="https://app.example.com",
        google_redirect_uri="https://api.example.com/auth/google/callback",
    )

    response = client.get(_callback_url(), follow_redirects=False)

    assert response.status_code == 302
    set_cookie = response.headers["set-cookie"]
    assert "SameSite=none" in set_cookie
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie


# --------------------------------------------------------------- demo login


def test_demo_login_issues_demo_session_cookie(make_auth_client: MakeClient) -> None:
    client = make_auth_client(google_client_id=None)

    response = client.post("/api/auth/demo-login")

    assert response.status_code == 200
    body = response.json()
    assert "token" not in body, "the session token must not be in the body"
    assert body["demo"] is True
    assert body["user"]["email"] == "demo@launchaudit.local"
    assert body["user"]["name"] == "Demo User"
    assert body["user"]["demo"] is True
    set_cookie = response.headers["set-cookie"]
    assert "launchaudit_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    claims = verify_session_token(_session_cookie(response), TEST_SESSION_SECRET)
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
    return _session_cookie(client.post("/api/auth/demo-login"))


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


def test_me_with_session_cookie_returns_user(
    make_auth_client: MakeClient, auth_client: TestClient
) -> None:
    token = _demo_token(make_auth_client)
    auth_client.cookies.set("launchaudit_session", token)

    response = auth_client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "demo@launchaudit.local"


def test_me_with_bad_session_cookie_is_401(auth_client: TestClient) -> None:
    auth_client.cookies.set("launchaudit_session", "not-a-session")

    response = auth_client.get("/api/auth/me")

    assert response.status_code == 401


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
        frontend_url="https://app.example.com",
    )
    assert settings_factory(environment="production").is_production

    response = production.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "demo@launchaudit.local"


def test_logout_returns_signed_out_and_clears_cookie(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"signed_out": True}
    set_cookie = response.headers["set-cookie"]
    assert "launchaudit_session=" in set_cookie
    assert "Max-Age=0" in set_cookie


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


def test_run_created_with_session_cookie_is_owned_not_guest(
    make_auth_client: MakeClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _demo_token(make_auth_client)
    client = make_auth_client(google_client_id=None)
    client.cookies.set("launchaudit_session", token)
    monkeypatch.setattr(runs_router, "execute_run", lambda *args, **kwargs: None)

    response = client.post(
        "/api/runs",
        data={"project_name": "Demo shop"},
        files={"zip_file": ("app.zip", _zip_bytes(), "application/zip")},
    )

    assert response.status_code == 201
    assert response.json()["is_guest"] is False


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
