"""Google OAuth2 sign-in: authorization URL, code exchange, ID token check.

All Google calls go through an injected httpx.Client so tests can use a
MockTransport; no test touches Google. The client secret and tokens are never
logged; failures surface as one safe message.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.core.errors import AppError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CODE_EXCHANGE_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_SCOPES = "openid email profile"


class GoogleAuthError(AppError):
    """Google sign-in failed. The message is safe to show the user."""

    def __init__(self) -> None:
        super().__init__("Sign-in failed. Try again.")


@dataclass(frozen=True, slots=True)
class GoogleProfile:
    """The verified identity Google returned for a signed-in user."""

    sub: str
    email: str
    name: str | None
    picture: str | None


def build_authorization_url(settings: Settings, state: str) -> str:
    """The Google sign-in URL the browser is sent to."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(client: httpx.Client, settings: Settings, code: str) -> str:
    """Swap an authorization code for an ID token. Returns the ID token."""
    try:
        response = client.post(
            GOOGLE_CODE_EXCHANGE_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret.get_secret_value()
                if settings.google_client_secret is not None
                else None,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
    except httpx.HTTPError:
        raise GoogleAuthError from None
    if response.status_code != 200:
        raise GoogleAuthError
    try:
        payload = response.json()
    except ValueError:
        raise GoogleAuthError from None
    id_token = payload.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise GoogleAuthError
    return id_token


def verify_id_token(client: httpx.Client, id_token: str, client_id: str) -> GoogleProfile:
    """Verify an ID token with Google's tokeninfo endpoint.

    Checks the audience is this app, the token has not expired, and the email
    is verified. Returns the profile Google attests to.
    """
    try:
        response = client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
    except httpx.HTTPError:
        raise GoogleAuthError from None
    if response.status_code != 200:
        raise GoogleAuthError
    try:
        claims = response.json()
    except ValueError:
        raise GoogleAuthError from None
    if claims.get("aud") != client_id:
        raise GoogleAuthError
    try:
        expires_at = int(claims.get("exp", 0))
    except (TypeError, ValueError):
        raise GoogleAuthError from None
    if expires_at <= int(time.time()):
        raise GoogleAuthError
    if claims.get("email_verified") != "true":
        raise GoogleAuthError
    sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(sub, str) or not sub or not isinstance(email, str) or not email:
        raise GoogleAuthError
    name = claims.get("name")
    picture = claims.get("picture")
    return GoogleProfile(
        sub=sub,
        email=email,
        name=name if isinstance(name, str) else None,
        picture=picture if isinstance(picture, str) else None,
    )
