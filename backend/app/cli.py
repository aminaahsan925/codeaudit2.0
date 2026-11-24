"""Local CLI: run a LaunchAudit from the terminal, no web UI, no database.

Usage (from the backend/ directory):

    python -m app.cli run --path ./my-app --live-url https://example.com

The CLI reuses the same services as the web run pipeline
(`app.services.runs.runner`): code scan, live checks, journey, dedupe,
scoring and report ordering. It runs in memory only: no run row is
created and no database is touched. Settings are built from explicit
values, never from the environment or backend/.env, so a local run can
never point at the real database.

Live checks and the journey only run when --live-url is given AND
--confirm-owns-domain is passed: the flag is the local equivalent of
the web domain-verification gate. Without it, live checks are skipped
with a note. The journey additionally needs --journey-user and
--journey-pass (a test account); without them it is skipped with a note.

Scanned code is read, never run, never imported. Journey screenshots
go to a temporary directory that is deleted when the run finishes.

Exit codes: 0 launch, 1 fix_first or do_not_launch, 2 usage or
validation error.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings, settings_from_values
from app.schemas.audit_run import Verdict
from app.schemas.finding import Finding
from app.services.journeys import JourneyCredentials, run_journey
from app.services.journeys.runner import JourneyTargetBlockedError
from app.services.live import run_live_checks_detailed
from app.services.report.report import count_by_severity, sort_fix_first
from app.services.report.scoring import compute_risk, verdict_for
from app.services.scan import ScanLimitError, dedupe_findings, run_code_scan

logger = logging.getLogger(__name__)

EXIT_LAUNCH = 0
EXIT_NOT_READY = 1
EXIT_USAGE_ERROR = 2

LIVE_SKIPPED_NO_CONFIRM = (
    "Live checks skipped: --live-url was given but --confirm-owns-domain "
    "was not passed, so the domain is not confirmed as yours."
)
JOURNEY_SKIPPED_NO_CREDENTIALS = (
    "Journey skipped: the default journey needs a test account, "
    "pass --journey-user and --journey-pass to run it."
)
JOURNEY_SKIPPED_NO_LIVE = "Journey skipped: no live URL was given."


def _cli_settings(artifact_dir: Path) -> Settings:
    """Settings for a local run: explicit values only, no real database.

    The database URL is an in-memory SQLite URL that is never opened:
    the CLI creates no session and writes no rows. Loopback live checks
    are allowed because the CLI runs on the owner's own machine and the
    user has explicitly confirmed they own the target domain.
    """
    return settings_from_values(
        environment="development",
        database_url="sqlite:///:memory:",
        artifact_dir=artifact_dir,
        allow_loopback_live_checks=True,
    )


def build_parser() -> argparse.ArgumentParser:
    """Argument parser for the CLI (exit code 2 on usage errors)."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description=(
            "Run a LaunchAudit locally, without the web UI. "
            "Exit codes: 0 launch, 1 fix_first or do_not_launch, "
            "2 usage or validation error."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run",
        help="Audit a local directory, optionally with live checks.",
        description=(
            "Audit a local directory. The code scan always runs. "
            "Live checks and the journey run only when --live-url is "
            "given together with --confirm-owns-domain."
        ),
    )
    run_parser.add_argument(
        "--path",
        required=True,
        help="Local directory to scan (required).",
    )
    run_parser.add_argument(
        "--live-url",
        default=None,
        help="Live app URL for live checks and the journey (optional).",
    )
    run_parser.add_argument(
        "--json",
        dest="json_file",
        default=None,
        metavar="FILE",
        help="Write the full report as JSON to FILE (optional).",
    )
    run_parser.add_argument(
        "--confirm-owns-domain",
        action="store_true",
        help=(
            "Confirm you own the --live-url domain. Required for live "
            "checks and the journey; without it they are skipped."
        ),
    )
    run_parser.add_argument(
        "--journey-user",
        default=None,
        help="Test-account email for the journey run (optional).",
    )
    run_parser.add_argument(
        "--journey-pass",
        default=None,
        help="Test-account password for the journey run (optional).",
    )
    return parser


def _finding_location(finding: Finding) -> str:
    """Where the finding is: file:line for code, URL for live findings."""
    if finding.file is not None:
        if finding.start_line is not None:
            return f"{finding.file}:{finding.start_line}"
        return finding.file
    if finding.evidence.http is not None:
        return finding.evidence.http.url
    return ""


def _validate_live_url(live_url: str) -> str | None:
    """Return an error message when the live URL is unusable, else None."""
    parsed = urlparse(live_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return f"Invalid --live-url {live_url!r}: use an http(s) URL with a host."
    return None


def _live_stage(
    live_url: str,
    settings: Settings,
    journey_user: str | None,
    journey_pass: str | None,
    notes: list[str],
) -> list[Finding]:
    """Live checks on a confirmed domain; a failed stage never fails the audit."""
    try:
        result = run_live_checks_detailed(live_url, settings, True, journey_user, journey_pass)
    except Exception:  # a failed live stage never fails the audit
        logger.exception("Local CLI: live checks could not finish.")
        notes.append("Live checks could not finish; continuing with the code scan.")
        return []
    if result.status == "skipped":
        notes.append(f"Live checks skipped: {result.skipped_reason}")
    return result.findings


def _journey_stage(
    live_url: str,
    settings: Settings,
    journey_user: str,
    journey_pass: str,
    notes: list[str],
) -> tuple[list[Finding], list[dict[str, Any]]]:
    """Journey run on a confirmed domain; a failed stage never fails the audit."""
    artifact_dir = settings.artifact_dir / "journey"
    try:
        result = run_journey(
            live_url,
            JourneyCredentials(email=journey_user, password=journey_pass),
            artifact_dir,
            settings,
        )
    except JourneyTargetBlockedError:
        notes.append("Journey skipped: the live target is blocked.")
        return [], []
    except Exception:  # a failed journey never fails the audit
        logger.exception("Local CLI: journey could not finish.")
        notes.append("Journey could not finish; continuing without it.")
        return [], []
    steps = [step.model_dump(mode="json") for step in result.steps]
    return result.findings, steps


def _print_report(
    verdict: Verdict,
    risk: float,
    findings: list[Finding],
    notes: list[str],
) -> None:
    """Terminal report: verdict, risk score, findings list."""
    for note in notes:
        print(note)
    print()
    print(f"Verdict: {verdict.value}")
    print(f"Risk: {risk:.1f}/10")
    print()
    if not findings:
        print("Findings: none.")
        return
    print(f"Findings ({len(findings)}):")
    for finding in findings:
        location = _finding_location(finding)
        suffix = f" ({location})" if location else ""
        print(f"  [{finding.severity.value}] {finding.title}{suffix}")


def _write_json_report(
    json_file: Path,
    *,
    path: str,
    live_url: str | None,
    verdict: Verdict,
    risk: float,
    findings: list[Finding],
    journey_steps: list[dict[str, Any]],
    notes: list[str],
) -> None:
    """Write the full report (verdict, risk, findings with proof) as JSON."""
    report = {
        "path": path,
        "live_url": live_url,
        "verdict": verdict.value,
        "risk_score": risk,
        "counts": count_by_severity(findings),
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "journey_steps": journey_steps,
        "notes": notes,
    }
    json_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _run_command(args: argparse.Namespace) -> int:
    """Run one local audit and return its exit code."""
    scan_path = Path(args.path)
    if not scan_path.is_dir():
        print(f"Error: --path {args.path!r} is not a directory.", file=sys.stderr)
        return EXIT_USAGE_ERROR
    if args.live_url is not None:
        error = _validate_live_url(args.live_url)
        if error is not None:
            print(f"Error: {error}", file=sys.stderr)
            return EXIT_USAGE_ERROR
    if (args.journey_user is None) != (args.journey_pass is None):
        print(
            "Error: --journey-user and --journey-pass must be given together.",
            file=sys.stderr,
        )
        return EXIT_USAGE_ERROR

    notes: list[str] = []
    print(f"LaunchAudit local run: {args.path}")

    with tempfile.TemporaryDirectory(prefix="launchaudit-cli-") as tmp:
        settings = _cli_settings(Path(tmp))
        try:
            code_findings = run_code_scan(scan_path).findings
        except ScanLimitError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return EXIT_USAGE_ERROR
        print(f"Code scan: {len(code_findings)} finding(s).")

        live_findings: list[Finding] = []
        journey_findings: list[Finding] = []
        journey_steps: list[dict[str, Any]] = []
        live_url = args.live_url
        if live_url is not None and not args.confirm_owns_domain:
            notes.append(LIVE_SKIPPED_NO_CONFIRM)
        if live_url is not None and args.confirm_owns_domain:
            live_findings = _live_stage(
                live_url, settings, args.journey_user, args.journey_pass, notes
            )
            print(f"Live checks: {len(live_findings)} finding(s).")
            if args.journey_user is not None and args.journey_pass is not None:
                journey_findings, journey_steps = _journey_stage(
                    live_url, settings, args.journey_user, args.journey_pass, notes
                )
                print(f"Journey: {len(journey_steps)} step(s), {len(journey_findings)} finding(s).")
            else:
                notes.append(JOURNEY_SKIPPED_NO_CREDENTIALS)
        elif args.live_url is None and (
            args.journey_user is not None or args.journey_pass is not None
        ):
            notes.append(JOURNEY_SKIPPED_NO_LIVE)

        findings = sort_fix_first(dedupe_findings(code_findings + live_findings + journey_findings))
        risk = compute_risk(findings)
        verdict = verdict_for(risk)

    _print_report(verdict, risk, findings, notes)

    if args.json_file is not None:
        try:
            _write_json_report(
                Path(args.json_file),
                path=args.path,
                live_url=args.live_url,
                verdict=verdict,
                risk=risk,
                findings=findings,
                journey_steps=journey_steps,
                notes=notes,
            )
        except OSError as exc:
            print(f"Error: could not write {args.json_file!r}: {exc}", file=sys.stderr)
            return EXIT_USAGE_ERROR
        print(f"\nFull report written to {args.json_file}")

    return EXIT_LAUNCH if verdict == Verdict.LAUNCH else EXIT_NOT_READY


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code.

    Usage errors exit via argparse with code 2 (SystemExit), matching
    the documented exit codes.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_command(args)
    parser.error(f"Unknown command: {args.command}")
    return EXIT_USAGE_ERROR  # unreachable: parser.error exits


if __name__ == "__main__":
    sys.exit(main())
