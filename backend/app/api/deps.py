"""Shared FastAPI dependencies (settings, auth, DB session)."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import UnauthorizedError
from app.core.security import Principal, verify_bearer_token
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


def authenticate_optional(
    settings: Settings,
    credentials: HTTPAuthorizationCredentials | None,
) -> Principal | None:
    """Validate an optional bearer token.

    Returns None when no token was presented (guest). Returns the principal
    for a valid token. Raises UnauthorizedError for a presented token that
    does not verify, so a bad token never silently becomes a guest.
    """
    if credentials is None:
        return None
    if settings.is_production:
        raise UnauthorizedError("Missing or invalid bearer token.")
    if not verify_bearer_token(credentials.credentials, settings.api_auth_token):
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
    """Accept only the configured API token; reject everything if none is set.

    Development stub until real auth lands: one shared token, compared in
    constant time, mapped to the subject "dev". It never authenticates anyone
    in production, even if settings validation were bypassed.
    """
    principal = authenticate_optional(settings, credentials)
    if principal is None:
        raise UnauthorizedError("Missing or invalid bearer token.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(require_auth)]
OptionalPrincipal = Annotated[Principal | None, Depends(optional_auth)]
