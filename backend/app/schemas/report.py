"""Launch Report: the assembled view of one audit run.

Mirrors `docs/api-contract.md` (Domain schemas -> Report). Built by
`app.services.report.report.build_report`, never constructed by hand in a
router.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.audit_run import AuditRun
from app.schemas.finding import Finding

# Optional/defaulted fields are still listed as `required` in the serialization
# schema, so generated client types are `T | null` instead of `T | undefined`.
_RESPONSE_CONFIG = ConfigDict(json_schema_serialization_defaults_required=True)


class JourneyStepView(BaseModel):
    """One journey step as shown on the report."""

    model_config = _RESPONSE_CONFIG

    name: str
    status: str
    screenshot_url: str | None = None
    error: str | None = None


class RerunDiff(BaseModel):
    """What changed between a rerun and the run before it."""

    model_config = _RESPONSE_CONFIG

    resolved: list[Finding] = Field(default_factory=list)
    still_open: list[Finding] = Field(default_factory=list)
    new: list[Finding] = Field(default_factory=list)


class ReportResponse(BaseModel):
    """Full report for one audit run, findings in fix-first order."""

    model_config = _RESPONSE_CONFIG

    run: AuditRun
    findings: list[Finding] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    journey_steps: list[JourneyStepView] = Field(default_factory=list)
    previous_risk_score: float | None = None
    resolved_findings: list[Finding] = Field(default_factory=list)
    score_change: float | None = None
