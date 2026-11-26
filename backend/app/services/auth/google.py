"""Google OAuth2 sign-in: authorization URL, code exchange, ID token check.

All Google calls go through an injected httpx.Client so tests can use a
MockTransport; no test touches Google. The client secret and tokens are never
logged; failures surface as one safe message.

The ID token is verified locally against Google's published signing keys
(JWKS): the signature, audience, issuer and expiry are all checked here, so
the token itself is never sent back to Google and no debugging endpoint is
involved. The key set is fetched fresh for each sign-in, so a rotated key is
never stale; sign-in is infrequent enough that one extra HTTPS call per
callback is acceptable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.core.config import Settings
from app.core.errors import AppError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CODE_EXCHANGE_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_SCOPES = "openid email profile"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


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


def _fetch_jwks(client: httpx.Client) -> list[dict]:
    """Fetch Google's current signing keys. Returns the `keys` list."""
    try:
        response = client.get(GOOGLE_JWKS_URL, headers={"Accept": "application/json"})
    except httpx.HTTPError:
        raise GoogleAuthError from None
    if response.status_code != 200:
        raise GoogleAuthError
    try:
        payload = response.json()
    except ValueError:
        raise GoogleAuthError from None
    keys = payload.get("keys")
    if not isinstance(keys, list) or not keys:
        raise GoogleAuthError
    return keys


def _key_for_token(keys: list[dict], kid: str | None) -> Any | None:
    """The public key object for the signing key id, or None when unknown."""
    for entry in keys:
        if not isinstance(entry, dict) or entry.get("kid") != kid:
            continue
        try:
            return RSAAlgorithm.from_jwk(json.dumps(entry))
        except (ValueError, KeyError, TypeError):
            return None
    return None


def verify_id_token(client: httpx.Client, id_token: str, client_id: str) -> GoogleProfile:
    """Verify an ID token locally against Google's signing keys.

    Checks the RS256 signature with the key the token names, the audience is
    this app, the issuer is Google, the token has not expired, and the email
    is verified. Returns the profile Google attests to.
    """
    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError:
        raise GoogleAuthError from None
    if header.get("alg") != "RS256":
        raise GoogleAuthError
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise GoogleAuthError
    public_key = _key_for_token(_fetch_jwks(client), kid)
    if public_key is None:
        raise GoogleAuthError
    try:
        claims = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=GOOGLE_ISSUERS,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError:
        raise GoogleAuthError from None
    if claims.get("email_verified") not in (True, "true"):
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
