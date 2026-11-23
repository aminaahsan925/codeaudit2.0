"""Journey runner tests against the old demo apps.

The broken demo app (port 8001) fails at checkout with an HTTP 500 payment
error; the fixed demo app (port 8002) passes the whole journey. Both apps
are started as subprocesses from ~/workspace/projects/launchaudit/demo-app/
using that project's own venv, and killed afterwards.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.schemas.finding import FindingEngine, Severity
from app.services.journeys import (
    JourneyCredentials,
    JourneyStepStatus,
    JourneyTargetBlockedError,
    run_journey,
)

DEMO_APP_DIR = Path.home() / "workspace" / "projects" / "launchaudit" / "demo-app"
DEMO_VENV_PYTHON = DEMO_APP_DIR / "venv" / "bin" / "python"
BROKEN_PORT = 8001
FIXED_PORT = 8002
STARTUP_TIMEOUT_SECONDS = 30.0

# Test-only password for the throwaway journey account; not a real secret.
TEST_PASSWORD = "TestPass123"  # noqa: S105
STEP_SCREENSHOTS = (
    "step-01-signup.png",
    "step-02-login.png",
    "step-03-cart.png",
    "step-04-checkout.png",
)


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
            # trust_env=False: the probe targets localhost directly and must
            # not consult the VM's proxy variables (whose no_proxy list
            # httpx cannot parse).
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


def _fresh_credentials() -> JourneyCredentials:
    """A unique test account per run, so sign up always creates it fresh."""
    return JourneyCredentials(
        email=f"journey-{uuid.uuid4().hex[:8]}@launchaudit.local",
        password=TEST_PASSWORD,
    )


def test_broken_app_journey_fails_at_checkout(
    broken_app_url: str,
    settings_factory,
    tmp_path: Path,
) -> None:
    settings: Settings = settings_factory(allow_loopback_live_checks=True)
    artifact_dir = tmp_path / "broken-artifacts"

    result = run_journey(broken_app_url, _fresh_credentials(), artifact_dir, settings)

    assert [step.name for step in result.steps] == [
        "Sign up",
        "Log in",
        "Add to cart",
        "Check out",
    ]
    assert [step.status for step in result.steps] == [
        JourneyStepStatus.PASSED,
        JourneyStepStatus.PASSED,
        JourneyStepStatus.PASSED,
        JourneyStepStatus.FAILED,
    ]
    assert result.steps[3].error is not None
    assert "payment" in result.steps[3].error.lower()

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.severity == Severity.HIGH
    assert finding.engine == FindingEngine.JOURNEY
    assert "checkout" in finding.title.lower()
    assert finding.evidence.screenshot_url == "step-04-checkout.png"
    assert finding.evidence.notes is not None
    assert "Check out" in finding.evidence.notes
    assert finding.fix_guidance is not None
    assert "Why it matters" in finding.fix_guidance
    assert "How to fix" in finding.fix_guidance

    for filename in STEP_SCREENSHOTS:
        assert (artifact_dir / filename).is_file()


def test_fixed_app_journey_passes(
    fixed_app_url: str,
    settings_factory,
    tmp_path: Path,
) -> None:
    settings: Settings = settings_factory(allow_loopback_live_checks=True)
    artifact_dir = tmp_path / "fixed-artifacts"

    result = run_journey(fixed_app_url, _fresh_credentials(), artifact_dir, settings)

    assert [step.status for step in result.steps] == [JourneyStepStatus.PASSED] * 4
    assert result.findings == []
    for filename in STEP_SCREENSHOTS:
        assert (artifact_dir / filename).is_file()


def test_loopback_blocked_without_setting(settings_factory, tmp_path: Path) -> None:
    settings: Settings = settings_factory(allow_loopback_live_checks=False)
    with pytest.raises(JourneyTargetBlockedError, match="loopback or private"):
        run_journey(
            "http://127.0.0.1:8001",
            _fresh_credentials(),
            tmp_path / "artifacts",
            settings,
        )


def test_loopback_blocked_in_production_even_when_enabled(settings_factory, tmp_path: Path) -> None:
    settings: Settings = settings_factory(environment="production", allow_loopback_live_checks=True)
    with pytest.raises(JourneyTargetBlockedError, match="loopback or private"):
        run_journey(
            "http://127.0.0.1:8001",
            _fresh_credentials(),
            tmp_path / "artifacts",
            settings,
        )


def test_public_target_passes_the_guard(settings_factory, tmp_path: Path) -> None:
    """The guard only blocks loopback/private targets, not public ones.

    No browser is launched here: the guard is checked directly, since a
    real public shop is out of scope for this test run.
    """
    from app.services.journeys.runner import _check_target_allowed

    settings: Settings = settings_factory(allow_loopback_live_checks=False)
    _check_target_allowed("https://example.com", settings)
    _check_target_allowed("https://shop.example.org:8443/store", settings)


def test_loopback_variants_are_blocked(settings_factory) -> None:
    from app.services.journeys.runner import _is_loopback_or_private

    assert _is_loopback_or_private("localhost") is True
    assert _is_loopback_or_private("127.0.0.1") is True
    assert _is_loopback_or_private("10.0.0.5") is True
    assert _is_loopback_or_private("192.168.1.20") is True
    assert _is_loopback_or_private("172.16.0.9") is True
    assert _is_loopback_or_private("::1") is True
    assert _is_loopback_or_private("169.254.169.254") is True
    assert _is_loopback_or_private("printer.local") is True
    assert _is_loopback_or_private("example.com") is False
    assert _is_loopback_or_private("8.8.8.8") is False
