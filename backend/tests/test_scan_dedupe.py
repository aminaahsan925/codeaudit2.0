"""Tests for dedupe_findings (PORTING-NOTES.md dedupe rules)."""

from app.schemas.finding import FindingEngine, Severity
from app.services.scan.dedupe import dedupe_findings, sort_findings
from app.services.scan.rules import make_finding


def _finding(rule_id: str, engine: FindingEngine, file: str | None, line: int | None):
    return make_finding(
        rule_id=rule_id,
        engine=engine,
        file=file,
        start_line=line,
        snippet_text="x",
    )


def test_tool_finding_at_native_location_dropped() -> None:
    findings = [
        _finding("SECRET_GENERIC", FindingEngine.NATIVE, "app.py", 10),
        _finding("semgrep:python.lang.security", FindingEngine.SEMGREP, "app.py", 10),
        _finding("SECRET_GIT_HISTORY", FindingEngine.GITLEAKS, "app.py", 10),
        _finding("CVE_DEP", FindingEngine.OSV, "requirements.txt", 3),
    ]
    kept = dedupe_findings(findings)
    assert [(f.rule_id, f.engine) for f in kept] == [
        ("SECRET_GENERIC", FindingEngine.NATIVE),
        ("CVE_DEP", FindingEngine.OSV),
    ]


def test_tool_finding_elsewhere_kept() -> None:
    findings = [
        _finding("SECRET_GENERIC", FindingEngine.NATIVE, "app.py", 10),
        _finding("semgrep:python.lang.security", FindingEngine.SEMGREP, "app.py", 11),
    ]
    assert len(dedupe_findings(findings)) == 2


def test_code_cors_dropped_when_live_cors_exists() -> None:
    findings = [
        _finding("CORS_WILDCARD", FindingEngine.NATIVE, "app.py", 30),
        _finding("CORS_OPEN", FindingEngine.LIVE, None, None),
        _finding("DEBUG_MODE", FindingEngine.NATIVE, "app.py", 21),
    ]
    kept = dedupe_findings(findings)
    assert [f.rule_id for f in kept] == ["CORS_OPEN", "DEBUG_MODE"]


def test_code_cors_kept_without_live_cors() -> None:
    findings = [
        _finding("CORS_WILDCARD", FindingEngine.NATIVE, "app.py", 30),
        _finding("DEBUG_MODE", FindingEngine.NATIVE, "app.py", 21),
    ]
    assert [f.rule_id for f in dedupe_findings(findings)] == [
        "CORS_WILDCARD",
        "DEBUG_MODE",
    ]


def test_dedupe_sorts_fix_first() -> None:
    findings = [
        _finding("DEBUG_MODE", FindingEngine.NATIVE, "app.py", 21),
        _finding("SECRET_GENERIC", FindingEngine.NATIVE, "app.py", 10),
        _finding("WEAK_PASSWORD_RULE", FindingEngine.NATIVE, "app.py", 15),
        _finding("SQL_INJECTION", FindingEngine.NATIVE, "app.py", 12),
    ]
    kept = dedupe_findings(findings)
    assert [f.severity for f in kept] == [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
    ]


def test_sort_findings_orders_by_file_then_line() -> None:
    findings = [
        _finding("DEBUG_MODE", FindingEngine.NATIVE, "b.py", 5),
        _finding("DEBUG_MODE", FindingEngine.NATIVE, "a.py", 9),
        _finding("DEBUG_MODE", FindingEngine.NATIVE, "a.py", 2),
    ]
    ordered = sort_findings(findings)
    assert [(f.file, f.start_line) for f in ordered] == [
        ("a.py", 2),
        ("a.py", 9),
        ("b.py", 5),
    ]
