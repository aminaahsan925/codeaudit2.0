"""User sign-in: link a Google profile to an account, or fetch the demo user."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.repositories.users import UserRepository
from app.schemas.user import User
from app.services.auth.google import GoogleProfile

DEMO_USER_EMAIL = "demo@launchaudit.local"
DEMO_USER_NAME = "Demo User"


def upsert_google_user(session: Session, profile: GoogleProfile) -> User:
    """Find the account for a Google profile, or create it.

    Lookup is by `google_sub`, the stable Google account id. A returning user
    gets their name, picture and email refreshed from Google. The insert is
    atomic (INSERT ... ON CONFLICT DO UPDATE), so two sign-ins for a new
    account racing each other cannot fail. The caller owns the transaction
    (commit or rollback).
    """
    return UserRepository(session).upsert_google_user(
        User(
            id=uuid4(),
            google_sub=profile.sub,
            email=profile.email,
            name=profile.name,
            picture_url=profile.picture,
            is_demo=False,
            created_at=datetime.now(UTC),
        )
    )


def get_or_create_demo_user(session: Session) -> User:
    """The single local demo account, created on first demo sign-in."""
    return UserRepository(session).get_or_create_demo_user(
        User(
            id=uuid4(),
            google_sub=None,
            email=DEMO_USER_EMAIL,
            name=DEMO_USER_NAME,
            picture_url=None,
            is_demo=True,
            created_at=datetime.now(UTC),
        )
    )
