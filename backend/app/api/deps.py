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


def require_auth(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    """Accept only the configured API token; reject everything if none is set.

    Development stub until real auth lands: one shared token, compared in
    constant time, mapped to the subject "dev". It never authenticates anyone
    in production, even if settings validation were bypassed.
    """
    if settings.is_production:
        raise UnauthorizedError("Missing or invalid bearer token.")
    token = credentials.credentials if credentials is not None else None
    if not verify_bearer_token(token, settings.api_auth_token):
        raise UnauthorizedError("Missing or invalid bearer token.")
    return Principal(subject="dev")


CurrentPrincipal = Annotated[Principal, Depends(require_auth)]
