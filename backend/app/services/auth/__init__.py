"""Auth services: Google OAuth and user sign-in."""

from app.services.auth.google import (
    GoogleAuthError,
    GoogleProfile,
    build_authorization_url,
    exchange_code,
    verify_id_token,
)
from app.services.auth.users import get_or_create_demo_user, upsert_google_user

__all__ = [
    "GoogleAuthError",
    "GoogleProfile",
    "build_authorization_url",
    "exchange_code",
    "get_or_create_demo_user",
    "upsert_google_user",
    "verify_id_token",
]
