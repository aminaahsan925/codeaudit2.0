"""Shared FastAPI dependencies (settings, auth, DB session)."""

from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import UnauthorizedError
from app.core.security import Principal, verify_bearer_token, verify_session_token
from app.db import get_db

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="`Authorization: Bearer <token>`",
)


def get_app_settings(request: Request) -> Settings:
    """The settings the running app was built with."""
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[Session, Depends(get_db)]


def get_http_client() -> Iterator[httpx.Client]:
    """Short-lived HTTP client for outbound calls (Google OAuth)."""
    with httpx.Client(timeout=10.0) as client:
        yield client


HttpClient = Annotated[httpx.Client, Depends(get_http_client)]


def authenticate_optional(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
) -> Principal | None:
    """Validate an optional bearer token.

    Returns None when no token was presented (guest). A valid session token
    gives the signed-in user's principal (in every environment). Otherwise
    the development token stub is tried, which never authenticates anyone in
    production. Raises UnauthorizedError for a presented token that does not
    verify, so a bad token never silently becomes a guest.
    """
    if credentials is None:
        return None
    token = credentials.credentials
    session_secret = settings.session_secret
    if session_secret is not None:
        claims = verify_session_token(token, session_secret.get_secret_value())
        if claims is not None:
            return Principal(
                subject=claims.email,
                user_id=claims.user_id,
                email=claims.email,
                name=claims.name,
                picture_url=claims.picture_url,
                demo=claims.demo,
            )
    if settings.is_production:
        raise UnauthorizedError("Missing or invalid bearer token.")
    if not verify_bearer_token(token, settings.api_auth_token):
        raise UnauthorizedError("Missing or invalid bearer token.")
    return Principal(subject="dev")


def optional_auth(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal | None:
    """Optional auth: a valid token gives a principal, no token gives None."""
    return authenticate_optional(settings, credentials)


def require_auth(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    """Accept a valid session token, or the development token stub outside
    production. Rejects everything when no token is presented or valid.
    """
    principal = authenticate_optional(settings, credentials)
    if principal is None:
        raise UnauthorizedError("Missing or invalid bearer token.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(require_auth)]
OptionalPrincipal = Annotated[Principal | None, Depends(optional_auth)]
