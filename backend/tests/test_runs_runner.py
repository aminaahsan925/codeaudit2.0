"""Audit-run pipeline tests against the old demo apps.

Demo loop targets (CONTRACT.md v2): the broken demo run lands risk 8.3,
verdict do_not_launch (planted secret 3.0, broken checkout 2.0, weak
password rule 1.0, missing security headers 1.0, insecure cookie 1.0,
debug mode 0.3); the fixed demo run lands risk 1.0, verdict launch
(CORS open to any origin only). Both apps are started as subprocesses
from ~/workspace/projects/launchaudit/demo-app/ using that project's own
venv, and killed afterwards.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import time
import uuid
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Base
from app.repositories.audit_runs import AuditRunRepository
from app.repositories.findings import FindingRepository
from app.schemas.audit_run import AuditRun, AuditRunStatus, Verdict
from app.schemas.finding import Finding, FindingStatus
from app.services.runs import execute_run

SettingsFactory = Callable[..., Settings]

DEMO_APP_DIR = Path.home() / "workspace" / "projects" / "launchaudit" / "demo-app"
DEMO_VENV_PYTHON = DEMO_APP_DIR / "venv" / "bin" / "python"
BROKEN_PORT = 8001
FIXED_PORT = 8002
STARTUP_TIMEOUT_SECONDS = 30.0

# Test-only password for the throwaway journey account; not a real secret.
TEST_PASSWORD = "TestPass123"  # noqa: S105


def _demo_apps_available() -> bool:
    return (
        DEMO_VENV_PYTHON.is_file()
        and (DEMO_APP_DIR / "broken" / "app.py").is_file()
        and (DEMO_APP_DIR / "fixed" / "app.py").is_file()
    )


def _wait_for_port(base_url: str, proc: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Demo app at {base_url} exited early (code {proc.returncode}).")
        try:
            httpx.get(base_url, timeout=2, trust_env=False)
        except httpx.HTTPError:
            time.sleep(0.2)
        else:
            return
    raise RuntimeError(f"Demo app at {base_url} did not answer within {timeout}s.")


def _serve_demo_app(variant: str, port: int) -> Iterator[str]:
    """Start one demo app variant on its port; kill it when done."""
    if not _demo_apps_available():
        pytest.skip("Old demo apps not present at ~/workspace/projects/launchaudit/demo-app/")
    env = {**os.environ, "PORT": str(port)}
    proc = subprocess.Popen(  # noqa: S603 - fixed local command, no user input
        [str(DEMO_VENV_PYTHON), "app.py"],
        cwd=DEMO_APP_DIR / variant,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_port(base_url, proc, STARTUP_TIMEOUT_SECONDS)
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


@pytest.fixture(scope="module")
def broken_app_url() -> Iterator[str]:
    """Serve the broken demo app on port 8001 for the module's tests."""
    yield from _serve_demo_app("broken", BROKEN_PORT)


@pytest.fixture(scope="module")
def fixed_app_url() -> Iterator[str]:
    """Serve the fixed demo app on port 8002 for the module's tests."""
    yield from _serve_demo_app("fixed", FIXED_PORT)


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[Callable[[], Session]]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'runs.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield maker
    engine.dispose()


@pytest.fixture
def run_settings(settings_factory: SettingsFactory, tmp_path: Path) -> Settings:
    return settings_factory(
        database_url=f"sqlite:///{tmp_path / 'runs.db'}",
        artifact_dir=tmp_path / "artifacts",
        allow_loopback_live_checks=True,
    )


def _create_run(session_factory: Callable[[], Session], **overrides: Any) -> AuditRun:
    values: dict[str, Any] = {
        "id": uuid4(),
        "project_name": "Demo app",
        "share_token": secrets.token_urlsafe(16),
    }
    values.update(overrides)
    run = AuditRun(**values)
    with session_factory() as session:
        created = AuditRunRepository(session).create(run)
        session.commit()
    return created


def _get_run(session_factory: Callable[[], Session], run_id: UUID) -> AuditRun | None:
    with session_factory() as session:
        return AuditRunRepository(session).get(run_id)


def _get_findings(session_factory: Callable[[], Session], run_id: UUID) -> list[Finding]:
    with session_factory() as session:
        return FindingRepository(session).list_for_run(run_id)


def _get_journey_steps(
    session_factory: Callable[[], Session], run_id: UUID
) -> list[dict[str, Any]] | None:
    with session_factory() as session:
        return AuditRunRepository(session).get_journey_steps(run_id)


def _zip_demo_tree(variant: str, dest: Path) -> Path:
    """Zip a demo app tree (code only, no runtime database)."""
    source = DEMO_APP_DIR / variant
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.suffix in {".db"} or "__pycache__" in path.parts:
                continue
            archive.write(path, path.relative_to(source))
    return dest


def _fresh_email() -> str:
    return f"audit-{uuid.uuid4().hex[:8]}@launchaudit.local"


# ------------------------------------------------------------- demo loop


def test_broken_demo_run(
    broken_app_url: str,
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    zip_path = _zip_demo_tree("broken", tmp_path / "broken.zip")
    run = _create_run(session_factory, live_url=broken_app_url)

    execute_run(
        run.id,
        run_settings,
        session_factory=session_factory,
        upload_path=zip_path,
        journey_email=_fresh_email(),
        journey_password=TEST_PASSWORD,
    )

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.SUCCEEDED
    assert finished.progress == 100
    assert finished.verdict == Verdict.DO_NOT_LAUNCH
    assert finished.risk_score == 8.3
    assert finished.started_at is not None
    assert finished.finished_at is not None
    assert finished.error is None
    assert finished.domain_verified is True

    findings = _get_findings(session_factory, run.id)
    assert {finding.rule_id for finding in findings} == {
        "SECRET_KNOWN_PREFIX",
        "JOURNEY_STEP_FAILED",
        "WEAK_PASSWORD_RULE",
        "DEBUG_MODE",
        "MISSING_SECURITY_HEADERS",
        "INSECURE_COOKIE",
    }
    journey_finding = next(f for f in findings if f.rule_id == "JOURNEY_STEP_FAILED")
    assert journey_finding.severity.value == "high"
    assert journey_finding.evidence.screenshot_url == (
        f"/api/runs/{run.id}/artifacts/step-04-checkout.png"
    )

    steps = _get_journey_steps(session_factory, run.id)
    assert steps is not None
    assert [step["name"] for step in steps] == [
        "Sign up",
        "Log in",
        "Add to cart",
        "Check out",
    ]
    assert [step["status"] for step in steps] == [
        "passed",
        "passed",
        "passed",
        "failed",
    ]
    assert "payment" in (steps[3]["error"] or "").lower()
    assert (run_settings.artifact_dir / str(run.id) / "step-04-checkout.png").is_file()


def test_fixed_demo_run(
    fixed_app_url: str,
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    zip_path = _zip_demo_tree("fixed", tmp_path / "fixed.zip")
    run = _create_run(session_factory, live_url=fixed_app_url)

    execute_run(
        run.id,
        run_settings,
        session_factory=session_factory,
        upload_path=zip_path,
        journey_email=_fresh_email(),
        journey_password=TEST_PASSWORD,
    )

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.SUCCEEDED
    assert finished.verdict == Verdict.LAUNCH
    assert finished.risk_score == 1.0
    assert finished.domain_verified is True

    findings = _get_findings(session_factory, run.id)
    # The code CORS finding is dropped: the live CORS finding wins.
    assert [(f.rule_id, f.engine.value) for f in findings] == [("CORS_OPEN", "live")]

    steps = _get_journey_steps(session_factory, run.id)
    assert steps is not None
    assert [step["status"] for step in steps] == ["passed"] * 4


def test_journey_skipped_without_credentials(
    broken_app_url: str,
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    zip_path = _zip_demo_tree("broken", tmp_path / "broken.zip")
    run = _create_run(session_factory, live_url=broken_app_url)

    execute_run(run.id, run_settings, session_factory=session_factory, upload_path=zip_path)

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.SUCCEEDED
    # Code 4.3 + missing headers 1.0. The insecure cookie is only visible
    # on the login response, so without credentials it is not observed.
    assert finished.risk_score == 5.3
    assert finished.verdict == Verdict.DO_NOT_LAUNCH
    assert _get_journey_steps(session_factory, run.id) is None
    findings = _get_findings(session_factory, run.id)
    assert all(finding.engine.value != "journey" for finding in findings)
    assert {finding.rule_id for finding in findings if finding.engine.value == "live"} == {
        "MISSING_SECURITY_HEADERS"
    }


# ------------------------------------------------------------------- rerun


def test_rerun_marks_resolved_findings_fixed(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    first = _create_run(session_factory)
    execute_run(
        first.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )
    first_finished = _get_run(session_factory, first.id)
    assert first_finished is not None
    assert first_finished.status == AuditRunStatus.SUCCEEDED
    assert first_finished.risk_score == 4.3
    assert first_finished.verdict == Verdict.FIX_FIRST

    second = _create_run(session_factory, previous_run_id=first.id)
    execute_run(
        second.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("fixed", tmp_path / "fixed.zip"),
    )
    second_finished = _get_run(session_factory, second.id)
    assert second_finished is not None
    assert second_finished.status == AuditRunStatus.SUCCEEDED
    # No live URL, so the code CORS finding survives (nothing to dedupe with).
    assert second_finished.risk_score == 1.0
    assert second_finished.verdict == Verdict.LAUNCH

    previous_findings = _get_findings(session_factory, first.id)
    assert len(previous_findings) == 3
    assert {finding.status for finding in previous_findings} == {FindingStatus.FIXED}


# ------------------------------------------------------- verification/skips


def test_unverified_domain_skips_live_checks(
    session_factory: Callable[[], Session],
    run_settings: Settings,
    tmp_path: Path,
) -> None:
    # A public host with no domain token: live checks are skipped, never run.
    run = _create_run(session_factory, live_url="https://example.com")

    execute_run(
        run.id,
        run_settings,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.SUCCEEDED
    assert finished.risk_score == 4.3
    assert finished.domain_verified is False
    findings = _get_findings(session_factory, run.id)
    assert all(finding.engine.value != "live" for finding in findings)


# ---------------------------------------------------------------- failures


def test_invalid_repo_url_fails_run_safely(
    session_factory: Callable[[], Session], run_settings: Settings
) -> None:
    run = _create_run(session_factory, repo_url="https://gitlab.com/example/shop")

    execute_run(run.id, run_settings, session_factory=session_factory)

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.FAILED
    assert finished.error == "The repo URL must be an https GitHub URL."
    assert finished.progress == 5
    assert finished.finished_at is not None


def test_missing_upload_fails_run_safely(
    session_factory: Callable[[], Session], run_settings: Settings, tmp_path: Path
) -> None:
    run = _create_run(session_factory)

    execute_run(
        run.id,
        run_settings,
        session_factory=session_factory,
        upload_path=tmp_path / "gone.zip",
    )

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.FAILED
    assert finished.error == "The uploaded code is no longer available."
    assert finished.progress == 5


def test_bad_zip_fails_run_safely(
    session_factory: Callable[[], Session], run_settings: Settings, tmp_path: Path
) -> None:
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"this is not a zip file")
    run = _create_run(session_factory)

    execute_run(run.id, run_settings, session_factory=session_factory, upload_path=bad_zip)

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.FAILED
    assert finished.error == "The uploaded zip file is not valid."


def test_zip_with_traversal_member_fails_run_safely(
    session_factory: Callable[[], Session], run_settings: Settings, tmp_path: Path
) -> None:
    evil_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil_zip, "w") as archive:
        archive.writestr("../evil.py", "x = 1\n")
    run = _create_run(session_factory)

    execute_run(run.id, run_settings, session_factory=session_factory, upload_path=evil_zip)

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.FAILED
    assert finished.error == "The zip file contains unsafe paths."
    assert not (tmp_path / "evil.py").exists()


def test_missing_run_is_a_noop(
    session_factory: Callable[[], Session], run_settings: Settings
) -> None:
    execute_run(uuid4(), run_settings, session_factory=session_factory)


# --------------------------------------------------------------- ai review


def test_review_fn_is_called(
    session_factory: Callable[[], Session], run_settings: Settings, tmp_path: Path
) -> None:
    seen: list[list[Finding]] = []

    def review(findings: list[Finding]) -> None:
        seen.append(list(findings))
        for finding in findings:
            finding.fix_guidance = "Reviewed."

    run = _create_run(session_factory)
    execute_run(
        run.id,
        run_settings,
        review,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )

    assert len(seen) == 1
    assert len(seen[0]) == 3
    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.SUCCEEDED
    findings = _get_findings(session_factory, run.id)
    assert all(finding.fix_guidance == "Reviewed." for finding in findings)


def test_review_fn_failure_does_not_fail_run(
    session_factory: Callable[[], Session], run_settings: Settings, tmp_path: Path
) -> None:
    def failing_review(findings: list[Finding]) -> None:
        raise RuntimeError("AI is down")

    run = _create_run(session_factory)
    execute_run(
        run.id,
        run_settings,
        failing_review,
        session_factory=session_factory,
        upload_path=_zip_demo_tree("broken", tmp_path / "broken.zip"),
    )

    finished = _get_run(session_factory, run.id)
    assert finished is not None
    assert finished.status == AuditRunStatus.SUCCEEDED
    assert finished.risk_score == 4.3
