"""Security primitives: response headers, request size limit, secret masking, token checks.

The two middlewares are pure ASGI (no BaseHTTPMiddleware) so they work with
streaming bodies and do not buffer responses.
"""

from __future__ import annotations

import hmac
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

import jwt
from pydantic import SecretStr
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.schemas.error import ErrorCode

MASK: Final = "••••"

_BASE_HEADERS: Final[tuple[tuple[str, str], ...]] = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
)
CONTENT_SECURITY_POLICY: Final = "default-src 'none'; frame-ancestors 'none'"
HSTS_VALUE: Final = "max-age=63072000; includeSubDomains"
API_PREFIX: Final = "/api"


# --------------------------------------------------------------------------- headers


def security_headers(
    path: str, *, hsts: bool, csp_exempt_paths: Iterable[str] = ()
) -> list[tuple[str, str]]:
    """Headers every response gets. Shared by the middleware and the 500 handler."""
    headers = list(_BASE_HEADERS)
    if path not in csp_exempt_paths:
        headers.append(("Content-Security-Policy", CONTENT_SECURITY_POLICY))
    if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
        headers.append(("Cache-Control", "no-store"))
    if hsts:
        headers.append(("Strict-Transport-Security", HSTS_VALUE))
    return headers


class SecurityHeadersMiddleware:
    """Add hardening headers to every HTTP response.

    `csp_exempt_paths` lets the interactive docs page (which loads its own
    scripts and styles) render outside production; JSON endpoints always get
    the locked-down CSP.
    """

    def __init__(
        self, app: ASGIApp, *, hsts: bool = False, csp_exempt_paths: Iterable[str] = ()
    ) -> None:
        self.app = app
        self.hsts = hsts
        self.csp_exempt_paths = frozenset(csp_exempt_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        extra = security_headers(
            scope.get("path", ""), hsts=self.hsts, csp_exempt_paths=self.csp_exempt_paths
        )

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in extra:
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)


# --------------------------------------------------------------------------- CORS


class CORSMiddlewareWithErrorEnvelope(CORSMiddleware):
    """Starlette's CORSMiddleware, but rejected preflights use the standard error body."""

    def preflight_response(self, request_headers: Headers) -> Response:
        response = super().preflight_response(request_headers)
        if response.status_code < 400:
            return response
        headers = {
            name: value
            for name, value in response.headers.items()
            if name not in ("content-length", "content-type")
        }
        return _error_json(
            400, ErrorCode.BAD_REQUEST, "CORS preflight request was rejected.", headers
        )


# ------------------------------------------------------------------- request size


def _error_json(
    status_code: int, code: ErrorCode, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    # Built here rather than in app.core.errors, which imports this module.
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code.value, "message": message}},
        headers=headers,
    )


def payload_too_large_response() -> JSONResponse:
    return _error_json(413, ErrorCode.PAYLOAD_TOO_LARGE, "Request body is too large.")


class PayloadTooLargeError(HTTPException):
    """Raised from `receive()` when the streamed body exceeds the limit."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Request body is too large.")


def _is_only_payload_too_large(exc: BaseException) -> bool:
    if isinstance(exc, PayloadTooLargeError):
        return True
    if isinstance(exc, BaseExceptionGroup):
        return all(_is_only_payload_too_large(inner) for inner in exc.exceptions)
    return False


class RequestSizeLimitMiddleware:
    """Reject request bodies larger than `max_bytes` with 413.

    Checks the declared Content-Length up front, then counts the bytes actually
    received so chunked or lying clients are cut off too.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > self.max_bytes:
            await payload_too_large_response()(scope, receive, send)
            return

        received = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            if exceeded:
                raise PayloadTooLargeError
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise PayloadTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except Exception as exc:
            # Normally the app's HTTPException handler already turned this into a
            # 413; this catches reads that happen outside the routing layer.
            if response_started or not _is_only_payload_too_large(exc):
                raise
            await payload_too_large_response()(scope, receive, send)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


# ------------------------------------------------------------------------ secrets


def mask_secret(value: str | None, *, visible: int = 4) -> str:
    """Mask a secret for display, keeping at most a short prefix.

    `mask_secret("tok_abcdef123456")` -> `"tok_••••"`. Values too short to
    keep a prefix safely (under 3x `visible` characters) are fully masked.
    """
    if not value:
        return MASK
    visible = max(visible, 0)
    if len(value) < visible * 3:
        return MASK
    return value[:visible] + MASK


# -------------------------------------------------------------------------- auth


@dataclass(frozen=True, slots=True)
class Principal:
    """Identity attached to an authenticated request.

    `subject` is the owner key for audit runs: the user's email for a session
    sign-in, `"dev"` for the development token stub. The user fields are only
    set for session sign-ins.
    """

    subject: str
    user_id: UUID | None = None
    email: str | None = None
    name: str | None = None
    picture_url: str | None = None
    demo: bool = False


def verify_bearer_token(provided: str | None, expected: SecretStr | None) -> bool:
    """Constant-time comparison of a presented bearer token with the configured one.

    Returns False when no token is configured, so an unset token rejects everything.
    """
    if expected is None or not provided:
        return False
    expected_value = expected.get_secret_value()
    if not expected_value:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected_value.encode("utf-8"))


# ----------------------------------------------------------------- session tokens

SESSION_ISSUER: Final = "launchaudit"
SESSION_TOKEN_EXPIRY_DAYS: Final = 30
OAUTH_STATE_EXPIRY_MINUTES: Final = 10
_OAUTH_STATE_PURPOSE: Final = "oauth-state"


@dataclass(frozen=True, slots=True)
class SessionClaims:
    """The identity a verified session token carries."""

    user_id: UUID
    email: str
    name: str | None
    picture_url: str | None
    demo: bool


def issue_session_token(
    secret: str,
    *,
    user_id: UUID,
    email: str,
    name: str | None,
    picture_url: str | None,
    demo: bool,
    expires_in_days: int = SESSION_TOKEN_EXPIRY_DAYS,
) -> str:
    """Sign a session token (HS256) for a signed-in user."""
    now = datetime.now(UTC)
    payload = {
        "iss": SESSION_ISSUER,
        "sub": str(user_id),
        "email": email,
        "name": name,
        "picture_url": picture_url,
        "demo": demo,
        "iat": now,
        "exp": now + timedelta(days=expires_in_days),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_session_token(token: str, secret: str) -> SessionClaims | None:
    """Verify a session token. Returns None for any bad, expired or alien token."""
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=SESSION_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    try:
        user_id = UUID(str(payload["sub"]))
        email = payload["email"]
        name = payload.get("name")
        picture_url = payload.get("picture_url")
        demo = payload.get("demo", False)
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    if (
        not isinstance(email, str)
        or not email
        or (name is not None and not isinstance(name, str))
        or (picture_url is not None and not isinstance(picture_url, str))
        or not isinstance(demo, bool)
    ):
        return None
    return SessionClaims(
        user_id=user_id, email=email, name=name, picture_url=picture_url, demo=demo
    )


def issue_oauth_state(secret: str, *, expires_in_minutes: int = OAUTH_STATE_EXPIRY_MINUTES) -> str:
    """Sign a short-lived OAuth `state` value (CSRF protection for the login flow)."""
    now = datetime.now(UTC)
    payload = {
        "iss": SESSION_ISSUER,
        "purpose": _OAUTH_STATE_PURPOSE,
        "nonce": secrets.token_hex(16),
        "iat": now,
        "exp": now + timedelta(minutes=expires_in_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_oauth_state(state: str, secret: str) -> bool:
    """True when `state` is a live state token we issued."""
    try:
        payload = jwt.decode(
            state,
            secret,
            algorithms=["HS256"],
            issuer=SESSION_ISSUER,
            options={"require": ["exp", "iat", "iss"]},
        )
    except jwt.PyJWTError:
        return False
    return payload.get("purpose") == _OAUTH_STATE_PURPOSE
