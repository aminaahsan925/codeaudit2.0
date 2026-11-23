"""Risk scoring: pure functions over Pydantic findings.

Weights and verdict bands come from the build contract (CONTRACT.md v2):
Critical 3.0, High 2.0, Medium 1.0, Low 0.3; risk is the sum capped at 10,
rounded to 1 decimal. Verdict: risk <= 2.0 launch, 2.1 to 5.0 fix first,
above 5.0 do not launch.
"""

from collections.abc import Sequence

from app.schemas.audit_run import Verdict
from app.schemas.finding import Finding, Severity

SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 3.0,
    Severity.HIGH: 2.0,
    Severity.MEDIUM: 1.0,
    Severity.LOW: 0.3,
}

MAX_RISK = 10.0
LAUNCH_MAX_RISK = 2.0
FIX_FIRST_MAX_RISK = 5.0


def severity_weight(severity: Severity) -> float:
    """Risk weight of one finding at this severity."""
    return SEVERITY_WEIGHTS[severity]


def compute_risk(findings: Sequence[Finding]) -> float:
    """Total risk of a finding set: capped sum of severity weights, 1 decimal."""
    total = sum(severity_weight(finding.severity) for finding in findings)
    return round(min(MAX_RISK, total), 1)


def verdict_for(risk: float) -> Verdict:
    """Launch verdict for a risk score."""
    if risk <= LAUNCH_MAX_RISK:
        return Verdict.LAUNCH
    if risk <= FIX_FIRST_MAX_RISK:
        return Verdict.FIX_FIRST
    return Verdict.DO_NOT_LAUNCH
