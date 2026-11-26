"""Tests for the report PDF: structure only, no byte-wise text assertions."""

from uuid import uuid4

from app.schemas.audit_run import AuditRun, Verdict
from app.schemas.finding import (
    Confidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
)
from app.schemas.report import JourneyStepView, ReportResponse
from app.services.report.pdf import render_report_pdf


def make_run(**overrides: object) -> AuditRun:
    values: dict[str, object] = {"id": uuid4(), "project_name": "Demo app"}
    values.update(overrides)
    return AuditRun(**values)


def make_finding(**overrides: object) -> Finding:
    values: dict[str, object] = {
        "id": uuid4(),
        "rule_id": "SECRET_GENERIC",
        "engine": FindingEngine.NATIVE,
        "category": FindingCategory.SECRETS,
        "severity": Severity.CRITICAL,
        "confidence": Confidence.HIGH,
        "title": "Hardcoded secret",
        "file": "app.py",
        "start_line": 12,
        "end_line": 12,
        "fix_guidance": "Move the key to the environment.",
    }
    values.update(overrides)
    return Finding(**values)


def make_report(**overrides: object) -> ReportResponse:
    values: dict[str, object] = {
        "run": make_run(verdict=Verdict.DO_NOT_LAUNCH, risk_score=8.3),
        "findings": [make_finding()],
        "counts": {"critical": 1, "high": 0, "medium": 0, "low": 0},
    }
    values.update(overrides)
    return ReportResponse(**values)


def test_pdf_starts_with_magic_bytes_and_is_nonempty() -> None:
    pdf = render_report_pdf(make_report())

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_pdf_for_empty_report() -> None:
    report = make_report(
        run=make_run(verdict=Verdict.LAUNCH, risk_score=0.0),
        findings=[],
        counts={"critical": 0, "high": 0, "medium": 0, "low": 0},
    )

    pdf = render_report_pdf(report)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_pdf_for_unscored_run() -> None:
    report = make_report(run=make_run(), findings=[], counts={})

    pdf = render_report_pdf(report)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_pdf_for_rerun_with_resolved_findings_and_journey() -> None:
    resolved = make_finding(
        rule_id="DEBUG_MODE",
        severity=Severity.LOW,
        category=FindingCategory.CONFIG,
        title="Debug mode on",
    )
    report = make_report(
        run=make_run(verdict=Verdict.LAUNCH, risk_score=1.0),
        previous_risk_score=8.3,
        resolved_findings=[resolved],
        score_change=-7.3,
        journey_steps=[
            JourneyStepView(name="Sign up", status="passed"),
            JourneyStepView(name="Check out", status="failed", error="Payment failed."),
        ],
    )

    pdf = render_report_pdf(report)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
