"""Tests for report assembly: ordering, counts, rerun diffs, score change."""

from uuid import uuid4

from app.schemas.audit_run import AuditRun, Verdict
from app.schemas.finding import (
    Confidence,
    Evidence,
    Finding,
    FindingCategory,
    FindingEngine,
    HttpEvidence,
    Severity,
)
from app.services.report.report import build_report, count_by_severity, diff_runs, sort_fix_first


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
    }
    values.update(overrides)
    return Finding(**values)


def test_sort_fix_first_orders_by_severity_then_rule_id() -> None:
    low = make_finding(rule_id="DEBUG_MODE", severity=Severity.LOW, title="Debug mode on")
    critical_b = make_finding(rule_id="SECRET_KNOWN_PREFIX", title="Known secret prefix")
    high = make_finding(
        rule_id="SQL_INJECTION",
        severity=Severity.HIGH,
        category=FindingCategory.INJECTION,
        title="SQL injection",
    )
    medium = make_finding(
        rule_id="CORS_WILDCARD",
        severity=Severity.MEDIUM,
        category=FindingCategory.CONFIG,
        title="CORS open",
    )
    critical_a = make_finding(rule_id="HARDCODED_CREDENTIAL", title="Hardcoded credential")

    ordered = sort_fix_first([low, critical_b, high, medium, critical_a])

    assert [f.rule_id for f in ordered] == [
        "HARDCODED_CREDENTIAL",
        "SECRET_KNOWN_PREFIX",
        "SQL_INJECTION",
        "CORS_WILDCARD",
        "DEBUG_MODE",
    ]


def test_count_by_severity() -> None:
    findings = [
        make_finding(rule_id="A", severity=Severity.CRITICAL),
        make_finding(rule_id="B", severity=Severity.HIGH),
        make_finding(rule_id="C", severity=Severity.HIGH),
        make_finding(rule_id="D", severity=Severity.MEDIUM),
    ]

    assert count_by_severity(findings) == {
        "critical": 1,
        "high": 2,
        "medium": 1,
        "low": 0,
    }
    assert count_by_severity([]) == {"critical": 0, "high": 0, "medium": 0, "low": 0}


def test_diff_runs_splits_resolved_still_open_new() -> None:
    fixed = make_finding(rule_id="DEBUG_MODE", severity=Severity.LOW, file="app.py", start_line=3)
    staying = make_finding(rule_id="SECRET_GENERIC", file="app.py", start_line=12)
    staying_again = make_finding(
        rule_id="SECRET_GENERIC", file="app.py", start_line=12, title="Hardcoded secret"
    )
    fresh = make_finding(rule_id="CORS_WILDCARD", severity=Severity.MEDIUM, file="app.py")

    diff = diff_runs([fixed, staying], [staying_again, fresh])

    assert [f.rule_id for f in diff.resolved] == ["DEBUG_MODE"]
    assert [f.rule_id for f in diff.still_open] == ["SECRET_GENERIC"]
    assert [f.rule_id for f in diff.new] == ["CORS_WILDCARD"]
    # still_open carries the current finding, resolved the previous one.
    assert diff.still_open[0].id == staying_again.id
    assert diff.resolved[0].id == fixed.id


def test_diff_runs_matches_journey_findings_by_step() -> None:
    previous = make_finding(
        engine=FindingEngine.JOURNEY,
        rule_id="JOURNEY_CHECKOUT_FAILS",
        severity=Severity.HIGH,
        file=None,
        start_line=None,
        end_line=None,
        evidence=Evidence(notes="Step: Check out"),
    )
    current = make_finding(
        engine=FindingEngine.JOURNEY,
        rule_id="JOURNEY_CHECKOUT_FAILS",
        severity=Severity.HIGH,
        file=None,
        start_line=None,
        end_line=None,
        evidence=Evidence(notes="Step: Check out"),
    )

    diff = diff_runs([previous], [current])

    assert diff.resolved == []
    assert [f.rule_id for f in diff.still_open] == ["JOURNEY_CHECKOUT_FAILS"]
    assert diff.new == []


def test_diff_runs_matches_live_findings_by_url() -> None:
    def live_finding() -> Finding:
        return make_finding(
            engine=FindingEngine.LIVE,
            rule_id="CORS_OPEN",
            severity=Severity.MEDIUM,
            file=None,
            start_line=None,
            end_line=None,
            evidence=Evidence(
                http=HttpEvidence(method="GET", url="https://shop.example.com/", status=200)
            ),
        )

    diff = diff_runs([live_finding()], [live_finding()])

    assert diff.resolved == []
    assert [f.rule_id for f in diff.still_open] == ["CORS_OPEN"]
    assert diff.new == []


def test_diff_runs_empty_previous_means_everything_new() -> None:
    diff = diff_runs([], [make_finding()])

    assert diff.resolved == []
    assert diff.still_open == []
    assert len(diff.new) == 1


def test_build_report_first_run() -> None:
    run = make_run(verdict=Verdict.DO_NOT_LAUNCH, risk_score=8.3)
    low = make_finding(rule_id="DEBUG_MODE", severity=Severity.LOW, title="Debug mode on")
    critical = make_finding(title="Hardcoded secret")
    steps = [
        {"name": "Sign up", "status": "passed", "screenshot": "/shots/signup.png"},
        {"name": "Check out", "status": "failed", "error": "Payment failed."},
    ]

    report = build_report(run, [low, critical], steps, None, None)

    assert report.run == run
    assert [f.rule_id for f in report.findings] == ["SECRET_GENERIC", "DEBUG_MODE"]
    assert report.counts == {"critical": 1, "high": 0, "medium": 0, "low": 1}
    assert [step.name for step in report.journey_steps] == ["Sign up", "Check out"]
    assert report.journey_steps[0].screenshot_url == "/shots/signup.png"
    assert report.journey_steps[0].status == "passed"
    assert report.journey_steps[1].error == "Payment failed."
    assert report.journey_steps[1].screenshot_url is None
    assert report.previous_risk_score is None
    assert report.resolved_findings == []
    assert report.score_change is None


def test_build_report_accepts_screenshot_url_key() -> None:
    run = make_run()
    steps = [{"name": "Log in", "status": "passed", "screenshot_url": "/shots/login.png"}]

    report = build_report(run, [], steps, None, None)

    assert report.journey_steps[0].screenshot_url == "/shots/login.png"


def test_build_report_rerun_diff_and_score_change() -> None:
    previous_run = make_run(verdict=Verdict.DO_NOT_LAUNCH, risk_score=8.3)
    run = make_run(verdict=Verdict.LAUNCH, risk_score=1.0)
    fixed = make_finding(rule_id="DEBUG_MODE", severity=Severity.LOW, file="app.py", start_line=3)
    staying = make_finding(file="app.py", start_line=12)
    staying_now = make_finding(file="app.py", start_line=12)

    report = build_report(run, [staying_now], None, previous_run, [fixed, staying])

    assert report.previous_risk_score == 8.3
    assert report.score_change == -7.3
    assert [f.rule_id for f in report.resolved_findings] == ["DEBUG_MODE"]
    assert [f.rule_id for f in report.findings] == ["SECRET_GENERIC"]


def test_build_report_score_change_none_without_previous_risk() -> None:
    previous_run = make_run(risk_score=None)
    run = make_run(risk_score=1.0)

    report = build_report(run, [], None, previous_run, [])

    assert report.previous_risk_score is None
    assert report.score_change is None


def test_build_report_score_change_rounds_to_one_decimal() -> None:
    previous_run = make_run(risk_score=5.0)
    run = make_run(risk_score=4.7)

    report = build_report(run, [], None, previous_run, [])

    assert report.score_change == -0.3


def test_build_report_empty() -> None:
    run = make_run(verdict=Verdict.LAUNCH, risk_score=0.0)

    report = build_report(run, [], None, None, None)

    assert report.findings == []
    assert report.counts == {"critical": 0, "high": 0, "medium": 0, "low": 0}
    assert report.journey_steps == []
    assert report.resolved_findings == []
    assert report.score_change is None
