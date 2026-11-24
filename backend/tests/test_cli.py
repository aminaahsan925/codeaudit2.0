"""Tests for the local CLI (`python -m app.cli run ...`).

The CLI is invoked through its `main()` function, not a subprocess.
External tools (semgrep, gitleaks, osv) are stubbed out like in
test_scan_runner.py: they are slow and networked, and their behaviour
is covered by test_scan_external.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import app.cli as cli
from app.schemas.finding import Finding, FindingEngine, Severity
from app.services.journeys.models import JourneyResult, JourneyStep, JourneyStepStatus
from app.services.live.runner import LiveCheckResult
from app.services.scan import runner as scan_runner
from app.services.scan.rules import make_finding

REPO_DEMO_APP_DIR = Path(__file__).resolve().parents[2] / "demo-app"

# Planted test keys, not real secrets.
FIXTURE_LINE_A = 'STRIPE_SECRET_KEY = "sk_test_9f2k7x4q8w1z3m5n7b0c"\n'  # gitleaks:allow
FIXTURE_LINE_B = 'GITHUB_TOKEN = "ghp_abcdefghijklmnop1234567890abcd1234"\n'  # gitleaks:allow


@pytest.fixture(autouse=True)
def _no_real_external_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        scan_runner, "run_external_tools", lambda *args, **kwargs: ([], ["native"], [])
    )


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _live_finding() -> Finding:
    return make_finding(
        rule_id="MISSING_SECURITY_HEADERS",
        engine=FindingEngine.LIVE,
        file=None,
        start_line=None,
        title="Missing security headers",
        severity=Severity.MEDIUM,
    )


def test_cli_broken_demo_code_scan_only(tmp_path: Path, capsys: Any) -> None:
    """Code scan on demo-app/broken: fix_first (risk 4.3), exit 1.

    The full web run on the broken demo reaches do_not_launch only with
    the live checks and journey added (missing headers, broken checkout);
    the code scan alone is the planted secret (3.0), weak password rule
    (1.0) and debug mode (0.3).
    """
    exit_code = cli.main(["run", "--path", str(REPO_DEMO_APP_DIR / "broken")])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "Verdict: fix_first" in out
    assert "Risk: 4.3/10" in out
    assert "[critical] Known secret key format in code (app.py:19)" in out
    assert "[medium] Weak password rule (app.py:162)" in out
    assert "[low] Debug mode is on (app.py:21)" in out


def test_cli_do_not_launch_fixture(tmp_path: Path, capsys: Any) -> None:
    """Two planted critical secrets score 6.0: do_not_launch, exit 1."""
    _write(tmp_path, "a.py", FIXTURE_LINE_A)
    _write(tmp_path, "b.py", FIXTURE_LINE_B)
    exit_code = cli.main(["run", "--path", str(tmp_path)])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "Verdict: do_not_launch" in out
    assert "Risk: 6.0/10" in out


def test_cli_clean_dir_launches(tmp_path: Path, capsys: Any) -> None:
    """A clean directory scores 0.0: launch, exit 0."""
    _write(tmp_path, "app.py", 'print("hello")\n')
    exit_code = cli.main(["run", "--path", str(tmp_path)])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Verdict: launch" in out
    assert "Risk: 0.0/10" in out
    assert "Findings: none." in out


def test_cli_json_writes_full_report(tmp_path: Path, capsys: Any) -> None:
    """--json writes valid JSON with verdict, risk and findings with proof."""
    json_file = tmp_path / "report.json"
    exit_code = cli.main(
        ["run", "--path", str(REPO_DEMO_APP_DIR / "broken"), "--json", str(json_file)]
    )
    out = capsys.readouterr().out
    assert exit_code == 1
    assert f"Full report written to {json_file}" in out
    report = json.loads(json_file.read_text())
    assert report["verdict"] == "fix_first"
    assert report["risk_score"] == 4.3
    assert report["counts"] == {"critical": 1, "high": 0, "medium": 1, "low": 1}
    assert len(report["findings"]) == 3
    first = report["findings"][0]
    assert first["severity"] == "critical"
    assert first["file"] == "app.py"
    assert first["start_line"] == 19
    assert first["snippet"]  # proof is present
    assert report["journey_steps"] == []
    assert isinstance(report["notes"], list)


def test_cli_live_url_without_confirm_skips_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    """--live-url without --confirm-owns-domain never probes the domain."""
    _write(tmp_path, "app.py", 'print("hello")\n')

    def _must_not_run(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("live checks must not run without confirmation")

    monkeypatch.setattr(cli, "run_live_checks_detailed", _must_not_run)
    monkeypatch.setattr(cli, "run_journey", _must_not_run)
    exit_code = cli.main(["run", "--path", str(tmp_path), "--live-url", "https://example.com"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Live checks skipped" in out
    assert "--confirm-owns-domain" in out


def test_cli_live_with_confirm_runs_live_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    """With --confirm-owns-domain, live checks run and feed the verdict."""
    _write(tmp_path, "app.py", 'print("hello")\n')
    calls: dict[str, Any] = {}

    def _fake_live(url: str, settings: Any, verified: bool, *args: Any) -> LiveCheckResult:
        calls["url"] = url
        calls["verified"] = verified
        return LiveCheckResult(findings=[_live_finding()])

    monkeypatch.setattr(cli, "run_live_checks_detailed", _fake_live)
    exit_code = cli.main(
        [
            "run",
            "--path",
            str(tmp_path),
            "--live-url",
            "https://example.com",
            "--confirm-owns-domain",
        ]
    )
    out = capsys.readouterr().out
    assert calls == {"url": "https://example.com", "verified": True}
    assert "Live checks: 1 finding(s)." in out
    assert "[medium] Missing security headers" in out
    # One medium live finding scores 1.0: still launch.
    assert "Verdict: launch" in out
    assert exit_code == 0
    # No journey credentials: the journey is skipped with a note.
    assert "Journey skipped" in out
    assert "--journey-user" in out


def test_cli_journey_runs_with_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Any
) -> None:
    """With live URL, confirmation and credentials, the journey runs."""
    _write(tmp_path, "app.py", 'print("hello")\n')
    calls: dict[str, Any] = {}

    def _fake_live(url: str, settings: Any, verified: bool, *args: Any) -> LiveCheckResult:
        return LiveCheckResult(findings=[])

    def _fake_journey(
        url: str, credentials: Any, artifact_dir: Any, settings: Any
    ) -> JourneyResult:
        calls["url"] = url
        calls["email"] = credentials.email
        return JourneyResult(
            steps=[
                JourneyStep(name="signup", status=JourneyStepStatus.PASSED),
                JourneyStep(name="login", status=JourneyStepStatus.PASSED),
            ],
            findings=[],
        )

    monkeypatch.setattr(cli, "run_live_checks_detailed", _fake_live)
    monkeypatch.setattr(cli, "run_journey", _fake_journey)
    exit_code = cli.main(
        [
            "run",
            "--path",
            str(tmp_path),
            "--live-url",
            "https://example.com",
            "--confirm-owns-domain",
            "--journey-user",
            "test@example.com",
            "--journey-pass",
            "test-password",
        ]
    )
    out = capsys.readouterr().out
    assert calls == {"url": "https://example.com", "email": "test@example.com"}
    assert "Journey: 2 step(s), 0 finding(s)." in out
    assert exit_code == 0


def test_cli_missing_path_is_usage_error(capsys: Any) -> None:
    """Argparse usage errors exit with code 2."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["run"])
    assert exc_info.value.code == 2


def test_cli_nonexistent_path_is_usage_error(tmp_path: Path, capsys: Any) -> None:
    """A --path that is not a directory returns exit code 2."""
    exit_code = cli.main(["run", "--path", str(tmp_path / "missing")])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "is not a directory" in err


def test_cli_invalid_live_url_is_usage_error(tmp_path: Path, capsys: Any) -> None:
    """A --live-url without an http(s) scheme and host returns exit code 2."""
    _write(tmp_path, "app.py", 'print("hello")\n')
    exit_code = cli.main(["run", "--path", str(tmp_path), "--live-url", "not-a-url"])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "Invalid --live-url" in err


def test_cli_half_journey_credentials_is_usage_error(tmp_path: Path, capsys: Any) -> None:
    """Only one of --journey-user / --journey-pass returns exit code 2."""
    _write(tmp_path, "app.py", 'print("hello")\n')
    exit_code = cli.main(["run", "--path", str(tmp_path), "--journey-user", "test@example.com"])
    err = capsys.readouterr().err
    assert exit_code == 2
    assert "must be given together" in err


def test_cli_help_documents_exit_codes(capsys: Any) -> None:
    """--help documents the exit codes."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])
    assert exc_info.value.code == 0
    out = " ".join(capsys.readouterr().out.split())  # help text wraps lines
    assert "0 launch" in out
    assert "1 fix_first or do_not_launch" in out
    assert "2 usage or validation error" in out
