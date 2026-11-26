"""Finding repository: the only code that reads/writes `findings`.

Public methods take and return Pydantic schemas (`app.schemas.finding`);
ORM rows never leave this module. Writes are flushed, not committed: the
caller owns the transaction.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.models.finding import FindingModel
from app.repositories.base import BaseRepository
from app.schemas.finding import (
    Confidence,
    Finding,
    FindingCategory,
    FindingEngine,
    FindingStatus,
    Severity,
)


def finding_key_for(finding: Finding) -> str:
    """Stable key for rerun diffs (see PORTING-NOTES.md).

    code/vibe: rule_id + "|" + file + ":" + line.
    journey: rule_id + "|" + step (from evidence.notes, "Step: <name>").
    live: rule_id + "|" + url.
    """
    if finding.engine == FindingEngine.JOURNEY:
        step = (finding.evidence.notes or "").removeprefix("Step: ").strip()
        return f"{finding.rule_id}|{step}"
    if finding.engine == FindingEngine.LIVE:
        url = finding.evidence.http.url if finding.evidence.http is not None else ""
        return f"{finding.rule_id}|{url}"
    return f"{finding.rule_id}|{finding.file or ''}:{finding.start_line or 0}"


def _model_to_schema(model: FindingModel) -> Finding:
    return Finding(
        id=model.id,
        rule_id=model.rule_id,
        engine=FindingEngine(model.engine),
        category=FindingCategory(model.category),
        severity=Severity(model.severity),
        confidence=Confidence(model.confidence),
        cwe=model.cwe,
        title=model.title,
        file=model.file,
        start_line=model.start_line,
        end_line=model.end_line,
        snippet=model.snippet,
        trace=model.trace or [],
        evidence=model.evidence or {},
        ai_verdict=model.ai_verdict,
        fix_guidance=model.fix_guidance,
        status=FindingStatus(model.status),
    )


def _schema_to_model(run_id: UUID, finding: Finding) -> FindingModel:
    return FindingModel(
        id=finding.id,
        run_id=run_id,
        rule_id=finding.rule_id,
        engine=finding.engine.value,
        category=finding.category.value,
        severity=finding.severity.value,
        confidence=finding.confidence.value,
        cwe=finding.cwe,
        title=finding.title,
        file=finding.file,
        start_line=finding.start_line,
        end_line=finding.end_line,
        snippet=finding.snippet,
        trace=[step.model_dump(mode="json") for step in finding.trace],
        evidence=finding.evidence.model_dump(mode="json"),
        ai_verdict=(
            finding.ai_verdict.model_dump(mode="json") if finding.ai_verdict is not None else None
        ),
        fix_guidance=finding.fix_guidance,
        status=finding.status.value,
        finding_key=finding_key_for(finding),
    )


class FindingRepository(BaseRepository[FindingModel]):
    """Create, read and update findings for an audit run."""

    model = FindingModel

    def create(self, run_id: UUID, finding: Finding) -> Finding:
        instance = self.add(_schema_to_model(run_id, finding))
        return _model_to_schema(instance)

    def create_many(self, run_id: UUID, findings: Sequence[Finding]) -> list[Finding]:
        instances = []
        for finding in findings:
            instances.append(self.add(_schema_to_model(run_id, finding)))
        return [_model_to_schema(instance) for instance in instances]

    def get(self, finding_id: UUID) -> Finding | None:  # type: ignore[override]
        model = super().get(finding_id)
        return _model_to_schema(model) if model is not None else None

    def list_for_run(self, run_id: UUID) -> list[Finding]:
        stmt = select(FindingModel).where(FindingModel.run_id == run_id)
        return [_model_to_schema(model) for model in self.session.scalars(stmt).all()]

    def get_by_finding_key(self, run_id: UUID, finding_key: str) -> Finding | None:
        stmt = select(FindingModel).where(
            FindingModel.run_id == run_id, FindingModel.finding_key == finding_key
        )
        model = self.session.scalars(stmt).first()
        return _model_to_schema(model) if model is not None else None

    def update_status(self, finding_id: UUID, *, status: FindingStatus) -> Finding | None:
        """Set a finding's status. Returns None when no finding has this id."""
        model = super().get(finding_id)
        if model is None:
            return None
        model.status = status.value
        self.session.flush()
        return _model_to_schema(model)
