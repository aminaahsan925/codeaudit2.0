"""AuditRun ORM model: one execution of the audit pipeline for a project.

Enum-valued columns (status, verdict) store the Pydantic schema values as
plain strings, so the schema stays portable between SQLite and Postgres.
Conversion between ORM rows and `app.schemas.audit_run.AuditRun` lives in
`app.repositories.audit_runs`, never here.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.finding import FindingModel


class AuditRunModel(Base):
    __tablename__ = "audit_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    live_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Journey steps as run: [{name, status, screenshot, error}]. Null when
    # no journey ran (no live URL, no credentials, or the journey was skipped).
    journey_steps: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    # The run this one re-audits (fix-and-verify rerun). No cascade: deleting
    # the previous run must not delete its reruns.
    previous_run_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("audit_runs.id"), nullable=True
    )
    # True once the live domain passed ownership verification (or the target
    # was a local address with loopback checks enabled outside production).
    domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    findings: Mapped[list[FindingModel]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
