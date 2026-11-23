"""Dedupe for a run's findings.

Two rules, from PORTING-NOTES.md:
1. Drop an external-tool finding whose (file, line) already has a native
   finding. The native rule is the sharper, project-aware signal.
2. Drop the code CORS finding (CORS_WILDCARD) when a live CORS finding
   (CORS_OPEN) exists for the same run. The live check is the proof.

Findings are returned in fix-first order: Critical, High, Medium, Low,
then by file and line.
"""

from app.schemas.finding import Finding, FindingEngine, Severity

TOOL_ENGINES = {
    FindingEngine.SEMGREP,
    FindingEngine.GITLEAKS,
    FindingEngine.OSV,
}

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


def sort_findings(findings: list[Finding]) -> list[Finding]:
    """Fix-first order: severity, then file, then line."""
    return sorted(
        findings,
        key=lambda f: (
            _SEVERITY_ORDER[f.severity],
            f.file or "",
            f.start_line or 0,
            f.rule_id,
        ),
    )


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    """Apply the dedupe rules and return the findings in fix-first order."""
    native_locations = {
        (f.file, f.start_line) for f in findings if f.engine == FindingEngine.NATIVE
    }
    live_cors = any(f.engine == FindingEngine.LIVE and f.rule_id == "CORS_OPEN" for f in findings)
    kept: list[Finding] = []
    for finding in findings:
        if (
            finding.engine in TOOL_ENGINES
            and (
                finding.file,
                finding.start_line,
            )
            in native_locations
        ):
            continue
        if (
            live_cors
            and finding.engine == FindingEngine.NATIVE
            and finding.rule_id == "CORS_WILDCARD"
        ):
            continue
        kept.append(finding)
    return sort_findings(kept)
