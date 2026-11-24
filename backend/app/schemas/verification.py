"""Schemas for server-issued domain verification."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DomainVerification(BaseModel):
    """One stored verification token, as held by the repository."""

    id: UUID
    domain: str
    token: str
    owner: str | None
    created_at: datetime
    verified_at: datetime | None


class VerificationTokenRequest(BaseModel):
    """Ask the server to issue a token for a domain."""

    domain: str = Field(min_length=1, max_length=253)


class VerificationTokenResponse(BaseModel):
    """The fresh token and the exact URL it must be served at."""

    domain: str
    token: str
    verification_url: str


class VerificationCheckRequest(BaseModel):
    """Ask the server to check the token file for a domain."""

    domain: str = Field(min_length=1, max_length=253)


class VerificationCheckResponse(BaseModel):
    """Whether the domain currently serves its stored token."""

    domain: str
    verified: bool
    verified_at: datetime | None
