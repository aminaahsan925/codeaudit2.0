"""Audit run repository: the only code that reads/writes `audit_runs`.

Public methods take and return Pydantic schemas (`app.schemas.audit_run`);
ORM rows never leave this module. Writes are flushed, not committed: the
caller owns the transaction.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.audit_run import AuditRunModel
from app.repositories.base import BaseRepository
from app.schemas.audit_run import AuditRun, AuditRunStatus, Verdict


def _ensure_aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; stored values are always UTC."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _model_to_schema(model: AuditRunModel) -> AuditRun:
    return AuditRun(
        id=model.id,
        project_name=model.project_name,
        repo_url=model.repo_url,
        live_url=model.live_url,
        status=AuditRunStatus(model.status),
        progress=model.progress,
        verdict=Verdict(model.verdict) if model.verdict is not None else None,
        risk_score=model.risk_score,
        started_at=_ensure_aware(model.started_at),
        finished_at=_ensure_aware(model.finished_at),
        error=model.error,
        share_token=model.share_token,
        is_guest=model.is_guest,
    )


def _schema_to_model(run: AuditRun, owner: str | None) -> AuditRunModel:
    return AuditRunModel(
        id=run.id,
        project_name=run.project_name,
        repo_url=str(run.repo_url) if run.repo_url is not None else None,
        live_url=str(run.live_url) if run.live_url is not None else None,
        status=run.status.value,
        progress=run.progress,
        verdict=run.verdict.value if run.verdict is not None else None,
        risk_score=run.risk_score,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error=run.error,
        share_token=run.share_token,
        is_guest=run.is_guest,
        owner=owner,
    )


class AuditRunRepository(BaseRepository[AuditRunModel]):
    """Create, read and update audit runs."""

    model = AuditRunModel

    def create(self, run: AuditRun, owner: str | None = None) -> AuditRun:
        """Persist a new run. `owner` is the owning user id, if any."""
        instance = self.add(_schema_to_model(run, owner))
        return _model_to_schema(instance)

    def get(self, run_id: UUID) -> AuditRun | None:  # type: ignore[override]
        model = super().get(run_id)
        return _model_to_schema(model) if model is not None else None

    def get_by_share_token(self, token: str) -> AuditRun | None:
        stmt = select(AuditRunModel).where(AuditRunModel.share_token == token)
        model = self.session.scalars(stmt).first()
        return _model_to_schema(model) if model is not None else None

    def update_status(
        self,
        run_id: UUID,
        *,
        status: AuditRunStatus | None = None,
        progress: int | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> AuditRun | None:
        """Update lifecycle fields; fields left as None are untouched.

        Returns None when no run has this id.
        """
        model = super().get(run_id)
        if model is None:
            return None
        if status is not None:
            model.status = status.value
        if progress is not None:
            model.progress = progress
        if error is not None:
            model.error = error
        if started_at is not None:
            model.started_at = started_at
        if finished_at is not None:
            model.finished_at = finished_at
        self.session.flush()
        return _model_to_schema(model)

    def update_result(
        self, run_id: UUID, *, verdict: Verdict, risk_score: float
    ) -> AuditRun | None:
        """Store the finished run's verdict and risk score."""
        model = super().get(run_id)
        if model is None:
            return None
        model.verdict = verdict.value
        model.risk_score = risk_score
        self.session.flush()
        return _model_to_schema(model)
