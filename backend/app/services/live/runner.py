"""Run the live checks against a verified domain.

The runner refuses unverified domains outright (DomainNotVerifiedError)
and never turns a failed request into a finding: an unreachable app or a
blocked target is reported as skipped, and a check that cannot run is
listed in `skipped_checks`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.core.config import Settings
from app.schemas.finding import Finding

from .checks import LiveAppUnreachableError, run_all_checks
from .ssrf_client import SsrfBlockedError, SsrfSafeClient
from .verify import DomainNotVerifiedError


@dataclass
class LiveCheckResult:
    """Outcome of a live-check run for the orchestrator to report on."""

    findings: list[Finding] = field(default_factory=list)
    status: Literal["done", "skipped"] = "done"
    skipped_reason: str | None = None
    skipped_checks: list[str] = field(default_factory=list)


def run_live_checks_detailed(
    url: str,
    settings: Settings,
    verified: bool,
    email: str | None = None,
    password: str | None = None,
) -> LiveCheckResult:
    """Run the live checks, returning findings plus skip information.

    Raises DomainNotVerifiedError when `verified` is False. An unreachable
    app, a blocked target, or a missing URL returns a skipped result
    instead of raising.
    """
    if not verified:
        raise DomainNotVerifiedError(
            "Live checks refused: the domain has not been verified. Request "
            "a verification token (POST /api/verification/token), serve it "
            "at https://<domain>/.well-known/launchaudit-verification.txt, "
            "then check it (POST /api/verification/check) and retry."
        )
    if not url or not url.strip():
        return LiveCheckResult(status="skipped", skipped_reason="No live app URL was given.")
    try:
        with SsrfSafeClient.from_settings(settings) as client:
            outcome = run_all_checks(client, url, email, password)
    except SsrfBlockedError as exc:
        return LiveCheckResult(
            status="skipped",
            skipped_reason=f"Live checks skipped: the target is blocked ({exc}).",
        )
    except LiveAppUnreachableError as exc:
        return LiveCheckResult(
            status="skipped",
            skipped_reason=f"Live checks skipped: {exc}.",
        )
    return LiveCheckResult(
        findings=outcome.findings,
        status="done",
        skipped_checks=outcome.skipped,
    )


def run_live_checks(
    url: str,
    settings: Settings,
    verified: bool,
    email: str | None = None,
    password: str | None = None,
) -> list[Finding]:
    """Run the live checks and return just the findings.

    Same behaviour as run_live_checks_detailed; use that when the caller
    needs to know why a run was skipped or which checks did not run.
    """
    return run_live_checks_detailed(url, settings, verified, email, password).findings
