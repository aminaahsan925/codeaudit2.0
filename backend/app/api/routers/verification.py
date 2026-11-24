"""Domain verification endpoints: request a server-issued token, then check it.

POST /api/verification/token issues a fresh random token for a domain and
tells the owner the exact URL to serve it at. POST /api/verification/check
fetches that exact well-known URL over HTTPS and compares it with the
stored token. A new token request for the same domain replaces the old
token, so only the latest token can verify.

Guests may verify too; their tokens are scoped by domain only, since a
guest has no identity. Signed-in owners are scoped by domain and subject.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter

from app.api.deps import DbSession, OptionalPrincipal, SettingsDep
from app.core.errors import AppError
from app.core.security import Principal
from app.repositories.domain_verifications import DomainVerificationRepository
from app.schemas.error import error_responses
from app.schemas.verification import (
    VerificationCheckRequest,
    VerificationCheckResponse,
    VerificationTokenRequest,
    VerificationTokenResponse,
)
from app.services.live.verify import (
    is_local_domain,
    normalize_domain,
    verification_url_for,
    verify_host_token,
)

router = APIRouter(prefix="/verification", tags=["verification"])


def _owner_of(principal: Principal | None) -> str | None:
    return principal.subject if principal is not None else None


@router.post(
    "/token",
    status_code=201,
    summary="Request a domain verification token",
    responses=error_responses(400),
)
def request_token(
    payload: VerificationTokenRequest,
    session: DbSession,
    principal: OptionalPrincipal,
) -> VerificationTokenResponse:
    domain = normalize_domain(payload.domain)
    if domain is None:
        raise AppError("Enter a valid domain, e.g. shop.example.com.")
    if is_local_domain(domain):
        raise AppError(
            "Local addresses do not need verification: loopback targets are "
            "verified automatically in development."
        )
    token = secrets.token_urlsafe(32)
    DomainVerificationRepository(session).issue(domain, _owner_of(principal), token)
    session.commit()
    return VerificationTokenResponse(
        domain=domain, token=token, verification_url=verification_url_for(domain)
    )


@router.post(
    "/check",
    summary="Check a domain verification file",
    responses=error_responses(400),
)
def check_domain(
    payload: VerificationCheckRequest,
    settings: SettingsDep,
    session: DbSession,
    principal: OptionalPrincipal,
) -> VerificationCheckResponse:
    domain = normalize_domain(payload.domain)
    if domain is None:
        raise AppError("Enter a valid domain, e.g. shop.example.com.")
    owner = _owner_of(principal)
    repository = DomainVerificationRepository(session)
    record = repository.get(domain, owner)
    if record is None:
        return VerificationCheckResponse(domain=domain, verified=False, verified_at=None)
    if verify_host_token(domain, record.token, settings):
        updated = repository.mark_verified(domain, owner)
        session.commit()
        verified_at = updated.verified_at if updated is not None else None
        return VerificationCheckResponse(domain=domain, verified=True, verified_at=verified_at)
    repository.clear_verified(domain, owner)
    session.commit()
    return VerificationCheckResponse(domain=domain, verified=False, verified_at=None)
