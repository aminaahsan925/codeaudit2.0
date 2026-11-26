"""Report assembly: pure functions over Pydantic models, no DB access.

Fix-first ordering is severity weight descending (Critical 3.0, High 2.0,
Medium 1.0, Low 0.3), then rule_id so the order is stable.
"""

from collections.abc import Sequence
from typing import Any

from app.repositories.findings import finding_key_for
from app.schemas.audit_run import AuditRun
from app.schemas.finding import Finding, Severity
from app.schemas.report import JourneyStepView, ReportResponse, RerunDiff
from app.services.report.scoring import SEVERITY_WEIGHTS


def sort_fix_first(findings: Sequence[Finding]) -> list[Finding]:
    """Most damaging first: severity weight desc, then rule_id."""
    return sorted(findings, key=lambda f: (-SEVERITY_WEIGHTS[f.severity], f.rule_id))


def count_by_severity(findings: Sequence[Finding]) -> dict[str, int]:
    """Finding counts keyed by lowercase severity name."""
    return {
        Severity.CRITICAL.value: sum(1 for f in findings if f.severity == Severity.CRITICAL),
        Severity.HIGH.value: sum(1 for f in findings if f.severity == Severity.HIGH),
        Severity.MEDIUM.value: sum(1 for f in findings if f.severity == Severity.MEDIUM),
        Severity.LOW.value: sum(1 for f in findings if f.severity == Severity.LOW),
    }


def diff_runs(
    previous_findings: Sequence[Finding], current_findings: Sequence[Finding]
) -> RerunDiff:
    """Diff two runs by stable finding key (see `finding_key_for`).

    resolved: previous findings whose key is absent now.
    still_open: current findings whose key was present before.
    new: current findings whose key was not present before.
    """
    previous_by_key = {finding_key_for(f): f for f in previous_findings}
    current_by_key = {finding_key_for(f): f for f in current_findings}
    resolved = [finding for key, finding in previous_by_key.items() if key not in current_by_key]
    still_open = [finding for key, finding in current_by_key.items() if key in previous_by_key]
    new = [finding for key, finding in current_by_key.items() if key not in previous_by_key]
    return RerunDiff(
        resolved=sort_fix_first(resolved),
        still_open=sort_fix_first(still_open),
        new=sort_fix_first(new),
    )


def _step_view(step: dict[str, Any]) -> JourneyStepView:
    """Normalise one stored journey-step dict into a view.

    Stored steps carry `screenshot` (journey runner shape) or
    `screenshot_url`; both are accepted.
    """
    screenshot = step.get("screenshot_url") or step.get("screenshot")
    return JourneyStepView(
        name=str(step.get("name", "")),
        status=str(step.get("status", "")),
        screenshot_url=str(screenshot) if screenshot is not None else None,
        error=str(step["error"]) if step.get("error") is not None else None,
    )


def build_report(
    run: AuditRun,
    findings: Sequence[Finding],
    journey_steps: Sequence[dict[str, Any]] | None,
    previous_run: AuditRun | None,
    previous_findings: Sequence[Finding] | None,
) -> ReportResponse:
    """Assemble the full report for one run.

    `journey_steps` are the run's stored step dicts (or None when the run
    has no journey). `previous_run` / `previous_findings` describe the run
    this one reran; both are None for a first run.
    """
    ordered = sort_fix_first(findings)
    steps = [_step_view(step) for step in journey_steps] if journey_steps else []
    previous_risk = previous_run.risk_score if previous_run is not None else None
    resolved: list[Finding] = []
    score_change: float | None = None
    if previous_findings is not None:
        resolved = diff_runs(previous_findings, findings).resolved
    if previous_risk is not None and run.risk_score is not None and previous_run is not None:
        score_change = round(run.risk_score - previous_risk, 1)
    return ReportResponse(
        run=run,
        findings=ordered,
        counts=count_by_severity(findings),
        journey_steps=steps,
        previous_risk_score=previous_risk,
        resolved_findings=resolved,
        score_change=score_change,
    )
