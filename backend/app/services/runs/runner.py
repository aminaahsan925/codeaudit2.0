"""Audit-run orchestrator: code scan, live checks, journey, AI review, score.

`execute_run` drives one run from queued to succeeded or failed, updating
the run row after every stage. It runs in a background thread (a FastAPI
BackgroundTask) and opens a fresh DB session per step, so a long pipeline
never holds a session open.

Scanned code is read, never run, never imported. Clones and extracted
trees live in a temp dir that is deleted when the run finishes, success or
fail. Journey credentials and the domain token exist only in memory for
the run and are never persisted.

Progress: 5 running, 15 code fetched, 40 code scan done, 60 live checks
done, 80 journey done, 85 dedupe done, 90 AI review done, 100 finished.
On failure the status becomes failed with a safe user-facing message and
progress stays where it was.
"""

from __future__ import annotations

import ipaddress
import logging
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db import get_sessionmaker
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.findings import FindingRepository, finding_key_for
from app.schemas.audit_run import AuditRun, AuditRunStatus
from app.schemas.finding import Finding, FindingStatus
from app.services.journeys import JourneyCredentials, run_journey
from app.services.journeys.runner import JourneyTargetBlockedError
from app.services.live import loopback_allowed, run_live_checks_detailed, verify_domain
from app.services.report.scoring import compute_risk, verdict_for
from app.services.scan import dedupe_findings, run_code_scan

from .code_input import CodeInputError, clone_repo, extract_zip, validate_github_url

logger = logging.getLogger(__name__)

# Review functions take the findings and either mutate them in place
# (returning None) or return the reviewed list.
ReviewFn = Callable[[list[Finding]], list[Finding] | None]
SessionFactory = Callable[[], Session]

GENERIC_FAILURE_MESSAGE = "The audit could not finish. Try running it again."
SKIPPED_NOT_VERIFIED = "domain not verified"


def _make_session(session_factory: SessionFactory | None) -> Session:
    maker = session_factory or get_sessionmaker()
    return maker()


def _load_run(session_factory: SessionFactory | None, run_id: UUID) -> AuditRun | None:
    with _make_session(session_factory) as session:
        return AuditRunRepository(session).get(run_id)


def _update_status(session_factory: SessionFactory | None, run_id: UUID, **kwargs: Any) -> None:
    with _make_session(session_factory) as session:
        AuditRunRepository(session).update_status(run_id, **kwargs)
        session.commit()


def _fail_run(session_factory: SessionFactory | None, run_id: UUID, message: str) -> None:
    """Mark the run failed with a safe message, keeping its progress."""
    try:
        _update_status(
            session_factory,
            run_id,
            status=AuditRunStatus.FAILED,
            error=message,
            finished_at=datetime.now(UTC),
        )
    except Exception:  # the failure update itself failed; log and move on
        logger.exception("Audit run %s: could not record the failure.", run_id)


def _is_loopback_or_private_host(hostname: str) -> bool:
    """True for localhost, .local names, and loopback/private IPs.

    No DNS lookup is performed: only literal addresses and local names are
    classified here, so a public hostname is never treated as local.
    """
    host = hostname.strip().lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local")):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


def _fetch_code(run: AuditRun, upload_path: Path | None, tmp_path: Path) -> Path:
    """Fetch the run's code tree into a temp dir. Raises CodeInputError."""
    if run.repo_url is not None:
        url = str(run.repo_url)
        if validate_github_url(url) is None:
            raise CodeInputError("The repo URL must be an https GitHub URL.")
        target = tmp_path / "repo"
        clone_repo(url, target)
        return target
    if upload_path is not None:
        target = tmp_path / "upload"
        extract_zip(upload_path, target)
        return target
    raise CodeInputError("No code was provided for this run.")


def _verify_live_domain(
    run: AuditRun,
    settings: Settings,
    session_factory: SessionFactory | None,
    domain_token: str | None,
) -> bool:
    """Whether the run's live URL may be probed.

    A loopback or private target counts as verified when loopback checks
    are enabled outside production; otherwise the domain token must
    verify. The run row is marked verified when the check passes. Both
    live checks and the journey use this one outcome: an unverified
    domain is never probed and never driven in a browser.
    """
    if run.live_url is None:
        return False
    live_url = str(run.live_url)
    host = urlparse(live_url).hostname or ""
    verified = False
    if _is_loopback_or_private_host(host) and loopback_allowed(settings):
        verified = True
        logger.info("Run %s: live target is local, treated as verified.", run.id)
    elif domain_token:
        verified = verify_domain(live_url, domain_token, settings)
    if verified:
        _update_domain_verified(session_factory, run.id)
    return verified


def _live_stage(
    run: AuditRun,
    settings: Settings,
    session_factory: SessionFactory | None,
    journey_email: str | None,
    journey_password: str | None,
    verified: bool,
) -> list[Finding]:
    """Live checks, or an empty list when they cannot run.

    Live checks run only on a verified domain. An unverified domain is
    skipped, never probed.
    """
    if run.live_url is None:
        return []
    if not verified:
        logger.info("Run %s: live checks skipped (%s).", run.id, SKIPPED_NOT_VERIFIED)
        return []
    live_url = str(run.live_url)
    try:
        result = run_live_checks_detailed(live_url, settings, True, journey_email, journey_password)
    except Exception:  # a failed live stage never fails the audit
        logger.exception("Run %s: live checks could not finish.", run.id)
        return []
    if result.status == "skipped":
        logger.info("Run %s: live checks skipped (%s).", run.id, result.skipped_reason)
    return result.findings


def _update_domain_verified(session_factory: SessionFactory | None, run_id: UUID) -> None:
    with _make_session(session_factory) as session:
        AuditRunRepository(session).update_domain_verified(run_id, verified=True)
        session.commit()


def _journey_stage(
    run: AuditRun,
    settings: Settings,
    session_factory: SessionFactory | None,
    journey_email: str | None,
    journey_password: str | None,
    verified: bool,
) -> list[Finding]:
    """Journey run, or an empty list when it cannot run.

    The journey needs a live URL, credentials, and a verified domain:
    the server never signs up, logs in, or clicks Pay on a site the
    submitter has not proven they own. Its steps are stored on the run,
    and finding screenshot names are prefixed with the run's artifact URL.
    """
    if run.live_url is None or not journey_email or not journey_password:
        logger.info("Run %s: journey skipped (no live URL or no credentials).", run.id)
        return []
    if not verified:
        logger.info("Run %s: journey skipped (%s).", run.id, SKIPPED_NOT_VERIFIED)
        return []
    artifact_dir = settings.artifact_dir / str(run.id)
    try:
        result = run_journey(
            str(run.live_url),
            JourneyCredentials(email=journey_email, password=journey_password),
            artifact_dir,
            settings,
        )
    except JourneyTargetBlockedError:
        logger.info("Run %s: journey skipped (target blocked).", run.id)
        return []
    except Exception:  # a failed journey never fails the audit
        logger.exception("Run %s: journey could not finish.", run.id)
        return []
    steps = [step.model_dump(mode="json") for step in result.steps]
    with _make_session(session_factory) as session:
        AuditRunRepository(session).update_journey_steps(run.id, steps)
        session.commit()
    prefix = f"/api/runs/{run.id}/artifacts/"
    findings: list[Finding] = []
    for finding in result.findings:
        screenshot = finding.evidence.screenshot_url
        if screenshot is None:
            findings.append(finding)
            continue
        evidence = finding.evidence.model_copy(update={"screenshot_url": prefix + screenshot})
        findings.append(finding.model_copy(update={"evidence": evidence}))
    return findings


def _ai_review_stage(
    findings: list[Finding], settings: Settings, review_fn: ReviewFn | None
) -> list[Finding]:
    """AI review, or the findings unchanged when review is unavailable.

    AI review never fails the run: an import failure, a missing module, or
    a review error all fall through to the unreviewed findings. An injected
    `review_fn` takes findings only; the real `review_findings` also needs
    settings (for provider keys), so it is called with both.
    """
    if review_fn is not None:
        try:
            reviewed = review_fn(findings)
        except Exception:  # AI review never fails the audit
            logger.exception("AI review failed; continuing with unreviewed findings.")
            return findings
        return list(reviewed) if reviewed is not None else findings
    try:
        from app.services.ai.review import review_findings
    except ImportError:
        logger.warning("AI review is not available; continuing without it.")
        return findings
    try:
        reviewed = review_findings(findings, settings)
    except Exception:  # AI review never fails the audit
        logger.exception("AI review failed; continuing with unreviewed findings.")
        return findings
    return list(reviewed) if reviewed is not None else findings


def _finish_run(
    session_factory: SessionFactory | None,
    run: AuditRun,
    findings: list[Finding],
) -> None:
    """Persist findings, mark resolved rerun findings fixed, finish the run."""
    risk = compute_risk(findings)
    verdict = verdict_for(risk)
    with _make_session(session_factory) as session:
        runs = AuditRunRepository(session)
        findings_repo = FindingRepository(session)
        findings_repo.create_many(run.id, findings)
        if run.previous_run_id is not None:
            # Rerun diff: previous findings absent now are resolved. The
            # report worker's diff_runs does not exist yet, so the key
            # comparison is inline (same stable keys as finding_key_for).
            current_keys = {finding_key_for(finding) for finding in findings}
            previous = findings_repo.list_for_run(run.previous_run_id)
            for old_finding in previous:
                if (
                    finding_key_for(old_finding) not in current_keys
                    and old_finding.status != FindingStatus.FIXED
                ):
                    findings_repo.update_status(old_finding.id, status=FindingStatus.FIXED)
        runs.update_status(
            run.id,
            status=AuditRunStatus.SUCCEEDED,
            progress=100,
            finished_at=datetime.now(UTC),
        )
        runs.update_result(run.id, verdict=verdict, risk_score=risk)
        session.commit()


def _run_pipeline(
    run: AuditRun,
    settings: Settings,
    review_fn: ReviewFn | None,
    session_factory: SessionFactory | None,
    upload_path: Path | None,
    journey_email: str | None,
    journey_password: str | None,
    domain_token: str | None,
) -> None:
    run_id = run.id
    _update_status(
        session_factory,
        run_id,
        status=AuditRunStatus.RUNNING,
        progress=5,
        started_at=datetime.now(UTC),
    )
    with tempfile.TemporaryDirectory(prefix="launchaudit-run-") as tmp:
        tree = _fetch_code(run, upload_path, Path(tmp))
        _update_status(session_factory, run_id, progress=15)
        code_findings = run_code_scan(tree).findings
        _update_status(session_factory, run_id, progress=40)
        verified = _verify_live_domain(run, settings, session_factory, domain_token)
        live_findings = _live_stage(
            run, settings, session_factory, journey_email, journey_password, verified
        )
        _update_status(session_factory, run_id, progress=60)
        journey_findings = _journey_stage(
            run, settings, session_factory, journey_email, journey_password, verified
        )
        _update_status(session_factory, run_id, progress=80)
        findings = dedupe_findings(code_findings + live_findings + journey_findings)
        _update_status(session_factory, run_id, progress=85)
        findings = _ai_review_stage(findings, settings, review_fn)
        _update_status(session_factory, run_id, progress=90)
    _finish_run(session_factory, run, findings)


def execute_run(
    run_id: UUID,
    settings: Settings,
    review_fn: ReviewFn | None = None,
    *,
    session_factory: SessionFactory | None = None,
    upload_path: Path | None = None,
    journey_email: str | None = None,
    journey_password: str | None = None,
    domain_token: str | None = None,
) -> None:
    """Run one audit to completion, updating the run row as stages finish.

    `upload_path` is the saved zip for upload runs (the router stores it at
    artifact_dir/{run_id}/upload.zip before starting this task); repo runs
    re-fetch from the run's repo_url. Journey credentials and the domain
    token are in-memory only and are never persisted. When `review_fn` is
    None, the AI review module is imported lazily and skipped if absent.
    """
    try:
        run = _load_run(session_factory, run_id)
    except Exception:  # nothing to update without a session
        logger.exception("Audit run %s: could not load the run.", run_id)
        return
    if run is None:
        logger.warning("Audit run %s not found; skipping.", run_id)
        return
    try:
        _run_pipeline(
            run,
            settings,
            review_fn,
            session_factory,
            upload_path,
            journey_email,
            journey_password,
            domain_token,
        )
    except CodeInputError as exc:
        logger.info("Audit run %s failed: %s", run_id, exc)
        _fail_run(session_factory, run_id, str(exc))
    except Exception:  # any pipeline failure fails the run safely
        logger.exception("Audit run %s failed.", run_id)
        _fail_run(session_factory, run_id, GENERIC_FAILURE_MESSAGE)
