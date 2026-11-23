"""Finding ORM model: one problem found by any engine, with its evidence.

Enum-valued columns (engine, category, severity, confidence, status) store
the Pydantic schema values as plain strings, so the schema stays portable
between SQLite and Postgres. Conversion between ORM rows and
`app.schemas.finding.Finding` lives in `app.repositories.findings`, never
here.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.audit_run import AuditRunModel


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    engine: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    cwe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    ai_verdict: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fix_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    finding_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    run: Mapped["AuditRunModel"] = relationship(back_populates="findings")
