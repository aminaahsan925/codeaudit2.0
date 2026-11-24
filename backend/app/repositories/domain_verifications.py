"""Domain verification repository: the only code that reads/writes
`domain_verifications`.

Public methods take and return Pydantic schemas
(`app.schemas.verification`); ORM rows never leave this module. Writes
are flushed, not committed: the caller owns the transaction.
"""

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.domain_verification import DomainVerificationModel
from app.repositories.base import BaseRepository
from app.schemas.verification import DomainVerification


def _ensure_aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; stored values are always UTC."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _model_to_schema(model: DomainVerificationModel) -> DomainVerification:
    return DomainVerification(
        id=model.id,
        domain=model.domain,
        token=model.token,
        owner=model.owner,
        created_at=_ensure_aware(model.created_at),  # type: ignore[arg-type]
        verified_at=_ensure_aware(model.verified_at),
    )


class DomainVerificationRepository(BaseRepository[DomainVerificationModel]):
    """Issue, read and mark server-issued domain verification tokens."""

    model = DomainVerificationModel

    def get(self, domain: str, owner: str | None) -> DomainVerification | None:  # type: ignore[override]
        """The stored token for a domain and owner, or None.

        A null owner matches guest-issued tokens only, so a signed-in
        caller never picks up a guest token and a guest never picks up
        an owned one.
        """
        stmt = select(DomainVerificationModel).where(
            DomainVerificationModel.domain == domain,
            DomainVerificationModel.owner.is_(None)
            if owner is None
            else DomainVerificationModel.owner == owner,
        )
        model = self.session.scalars(stmt).first()
        return _model_to_schema(model) if model is not None else None

    def issue(self, domain: str, owner: str | None, token: str) -> DomainVerification:
        """Store a fresh token for a domain and owner.

        A new request replaces the old token and clears the verified
        mark, so only the latest token can verify the domain.
        """
        stmt = select(DomainVerificationModel).where(
            DomainVerificationModel.domain == domain,
            DomainVerificationModel.owner.is_(None)
            if owner is None
            else DomainVerificationModel.owner == owner,
        )
        model = self.session.scalars(stmt).first()
        now = datetime.now(UTC)
        if model is None:
            model = self.add(
                DomainVerificationModel(domain=domain, token=token, owner=owner, created_at=now)
            )
        else:
            model.token = token
            model.created_at = now
            model.verified_at = None
            self.session.flush()
        return _model_to_schema(model)

    def mark_verified(self, domain: str, owner: str | None) -> DomainVerification | None:
        """Record that the domain served its stored token. None when missing."""
        model = self._find(domain, owner)
        if model is None:
            return None
        model.verified_at = datetime.now(UTC)
        self.session.flush()
        return _model_to_schema(model)

    def clear_verified(self, domain: str, owner: str | None) -> DomainVerification | None:
        """Clear the verified mark after a failed check. None when missing."""
        model = self._find(domain, owner)
        if model is None:
            return None
        model.verified_at = None
        self.session.flush()
        return _model_to_schema(model)

    def _find(self, domain: str, owner: str | None) -> DomainVerificationModel | None:
        stmt = select(DomainVerificationModel).where(
            DomainVerificationModel.domain == domain,
            DomainVerificationModel.owner.is_(None)
            if owner is None
            else DomainVerificationModel.owner == owner,
        )
        return self.session.scalars(stmt).first()
