from uuid import uuid4

import pytest

from app.schemas.audit_run import Verdict
from app.schemas.finding import (
    Confidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
)
from app.services.report.scoring import compute_risk, severity_weight, verdict_for


def make_finding(severity: Severity, rule_id: str = "TEST_RULE") -> Finding:
    return Finding(
        id=uuid4(),
        rule_id=rule_id,
        engine=FindingEngine.NATIVE,
        category=FindingCategory.OTHER,
        severity=severity,
        confidence=Confidence.HIGH,
        title="Test finding",
    )


@pytest.mark.parametrize(
    ("severity", "weight"),
    [
        (Severity.CRITICAL, 3.0),
        (Severity.HIGH, 2.0),
        (Severity.MEDIUM, 1.0),
        (Severity.LOW, 0.3),
    ],
)
def test_severity_weights(severity: Severity, weight: float) -> None:
    assert severity_weight(severity) == weight


def test_compute_risk_empty_is_zero() -> None:
    assert compute_risk([]) == 0.0


def test_compute_risk_sums_weights() -> None:
    findings = [make_finding(Severity.HIGH), make_finding(Severity.LOW)]

    assert compute_risk(findings) == 2.3


def test_compute_risk_caps_at_ten() -> None:
    findings = [make_finding(Severity.CRITICAL) for _ in range(5)]

    assert compute_risk(findings) == 10.0


def test_compute_risk_rounds_to_one_decimal() -> None:
    findings = [make_finding(Severity.LOW) for _ in range(3)]

    assert compute_risk(findings) == 0.9


@pytest.mark.parametrize(
    ("risk", "verdict"),
    [
        (0.0, Verdict.LAUNCH),
        (2.0, Verdict.LAUNCH),
        (2.1, Verdict.FIX_FIRST),
        (5.0, Verdict.FIX_FIRST),
        (5.1, Verdict.DO_NOT_LAUNCH),
        (10.0, Verdict.DO_NOT_LAUNCH),
    ],
)
def test_verdict_bands(risk: float, verdict: Verdict) -> None:
    assert verdict_for(risk) == verdict


def test_broken_demo_target_is_8_3_do_not_launch() -> None:
    """The broken demo run: planted secret, broken checkout, weak password
    rule, debug mode, missing security headers, insecure cookie."""
    findings = [
        make_finding(Severity.CRITICAL, "SECRET_GENERIC"),
        make_finding(Severity.HIGH, "JOURNEY_CHECKOUT_FAILS"),
        make_finding(Severity.MEDIUM, "WEAK_PASSWORD_RULE"),
        make_finding(Severity.LOW, "DEBUG_MODE"),
        make_finding(Severity.MEDIUM, "MISSING_SECURITY_HEADERS"),
        make_finding(Severity.MEDIUM, "INSECURE_COOKIE"),
    ]

    risk = compute_risk(findings)

    assert risk == 8.3
    assert verdict_for(risk) == Verdict.DO_NOT_LAUNCH


def test_fixed_demo_target_is_1_0_launch() -> None:
    """The fixed demo run: only CORS open to any origin remains."""
    findings = [make_finding(Severity.MEDIUM, "CORS_OPEN")]

    risk = compute_risk(findings)

    assert risk == 1.0
    assert verdict_for(risk) == Verdict.LAUNCH
