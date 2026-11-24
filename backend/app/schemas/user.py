"""User schema: one signed-in account (Google or demo)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    """A user account. `google_sub` is None for the local demo user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    google_sub: str | None
    email: str
    name: str | None
    picture_url: str | None
    is_demo: bool
    created_at: datetime
