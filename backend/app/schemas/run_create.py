"""Request schemas for the audit-run endpoints."""

from pydantic import BaseModel, Field


class RerunRequest(BaseModel):
    """Fresh per-run inputs for a rerun.

    Journey credentials are never persisted: a rerun copies only the
    project name, repo URL and live URL from the original run, so the
    caller supplies fresh credentials here. Domain verification uses
    the stored server-issued token for the domain and owner; no token
    is accepted from the client.
    """

    journey_email: str | None = Field(default=None, max_length=320)
    journey_password: str | None = Field(default=None, max_length=1024)
