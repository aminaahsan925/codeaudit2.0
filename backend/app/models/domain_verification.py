"""DomainVerification ORM model: one server-issued token per domain and owner.

The server generates the token when the owner asks for it; the owner
proves control of the domain by serving that token at the well-known
URL. A new request for the same domain and owner replaces the old token
and clears the verified mark, so only the latest token can verify.

`owner` is the signed-in user's subject, or null for a guest request.
Guest tokens are scoped by domain only, since a guest has no identity:
any guest run for that domain can use a guest-issued token.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DomainVerificationModel(Base):
    __tablename__ = "domain_verifications"
    __table_args__ = (
        UniqueConstraint("domain", "owner", name="uq_domain_verifications_domain_owner"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    token: Mapped[str] = mapped_column(String(128), nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
