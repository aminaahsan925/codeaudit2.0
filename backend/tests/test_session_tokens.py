"""Session token and OAuth state tests: issue, verify, expiry, tampering."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from starlette.responses import Response

from app.core.security import (
    SESSION_COOKIE_NAME,
    SESSION_ISSUER,
    clear_session_cookie,
    issue_oauth_state,
    issue_session_token,
    set_session_cookie,
    verify_oauth_state,
    verify_session_token,
)

# Fixed values for tests only; long enough to satisfy the minimum secret length.
SECRET = "test-session-secret-0123456789abcdef0123456789"  # noqa: S105
OTHER_SECRET = "other-session-secret-0123456789abcdef0123456789"  # noqa: S105


@pytest.fixture
def user_id():
    return uuid4()


def test_session_round_trip(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name="Amina",
        picture_url="https://example.com/pic.jpg",
        demo=False,
    )

    claims = verify_session_token(token, SECRET)

    assert claims is not None
    assert claims.user_id == user_id
    assert claims.email == "amina@example.com"
    assert claims.name == "Amina"
    assert claims.picture_url == "https://example.com/pic.jpg"
    assert claims.demo is False


def test_session_demo_flag_survives(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="demo@launchaudit.local",
        name="Demo User",
        picture_url=None,
        demo=True,
    )

    claims = verify_session_token(token, SECRET)

    assert claims is not None
    assert claims.demo is True
    assert claims.name == "Demo User"
    assert claims.picture_url is None


def test_session_expired_token_is_rejected(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
        expires_in_days=-1,
    )

    assert verify_session_token(token, SECRET) is None


def test_session_wrong_secret_is_rejected(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
    )

    assert verify_session_token(token, OTHER_SECRET) is None


def test_session_tampered_token_is_rejected(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
    )
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")

    assert verify_session_token(tampered, SECRET) is None


@pytest.mark.parametrize("bad_token", ["", "not-a-token", "a.b", "a.b.c.d"])
def test_session_malformed_token_is_rejected(bad_token: str) -> None:
    assert verify_session_token(bad_token, SECRET) is None


def test_session_token_without_expiry_is_rejected(user_id) -> None:
    token = jwt.encode(
        {"iss": SESSION_ISSUER, "sub": str(user_id), "email": "a@example.com"},
        SECRET,
        algorithm="HS256",
    )

    assert verify_session_token(token, SECRET) is None


def test_session_token_with_wrong_issuer_is_rejected(user_id) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": "someone-else",
            "sub": str(user_id),
            "email": "a@example.com",
            "iat": now,
            "exp": now + timedelta(days=1),
        },
        SECRET,
        algorithm="HS256",
    )

    assert verify_session_token(token, SECRET) is None


def test_oauth_state_round_trip() -> None:
    state = issue_oauth_state(SECRET)

    assert verify_oauth_state(state, SECRET) is True


def test_oauth_state_wrong_secret_is_rejected() -> None:
    state = issue_oauth_state(SECRET)

    assert verify_oauth_state(state, OTHER_SECRET) is False


def test_oauth_state_expired_is_rejected() -> None:
    state = issue_oauth_state(SECRET, expires_in_minutes=-1)

    assert verify_oauth_state(state, SECRET) is False


def test_oauth_state_malformed_is_rejected() -> None:
    assert verify_oauth_state("not-a-state", SECRET) is False


def test_session_token_is_not_a_valid_oauth_state(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
    )

    assert verify_oauth_state(token, SECRET) is False


def test_session_cookie_is_httponly_and_lax_outside_production(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
    )
    response = Response()
    set_session_cookie(response, token, production=False)

    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE_NAME}={token}" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Secure" not in cookie
    assert "Max-Age=2592000" in cookie
    assert "Path=/" in cookie


def test_session_cookie_is_secure_and_cross_site_in_production(user_id) -> None:
    token = issue_session_token(
        SECRET,
        user_id=user_id,
        email="amina@example.com",
        name=None,
        picture_url=None,
        demo=False,
    )
    response = Response()
    set_session_cookie(response, token, production=True)

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=none" in cookie
    assert "Secure" in cookie


def test_clear_session_cookie_expires_it() -> None:
    response = Response()
    clear_session_cookie(response, production=False)

    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE_NAME}=" in cookie
    assert "Max-Age=0" in cookie
    assert "HttpOnly" in cookie
