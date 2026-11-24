"""Tests for the external scanners (semgrep, gitleaks, osv, pip-audit).

All subprocess calls are mocked: no real tool runs here. Fake key-shaped
values carry an inline `gitleaks:allow` comment.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.schemas.finding import FindingEngine, Severity
from app.services.scan import external
from app.services.scan.external import run_external_tools
from app.services.scan.rules import make_finding


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class _FakeRun:
    """Dispatch fake subprocess results by binary name."""

    def __init__(self, outputs: dict[str, object]):
        self.outputs = outputs
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], **kwargs):
        self.commands.append(command)
        name = Path(command[0]).name
        result = self.outputs[name]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def fake_tools(monkeypatch):
    """Install fake find_tool + subprocess.run. Returns the _FakeRun."""

    def _install(outputs: dict[str, object], installed: set[str]):
        fake_run = _FakeRun(outputs)
        monkeypatch.setattr(external.subprocess, "run", fake_run)
        monkeypatch.setattr(
            external,
            "find_tool",
            lambda name, tools_dir=None: f"/fake/{name}" if name in installed else None,
        )
        return fake_run

    return _install


def _native_finding(file: str, line: int):
    return make_finding(
        rule_id="SECRET_GENERIC",
        engine=FindingEngine.NATIVE,
        file=file,
        start_line=line,
        snippet_text="x",
    )


def _semgrep_result(tree: Path, check_id: str, severity: str, line: int) -> dict:
    return {
        "check_id": check_id,
        "path": str(tree / "app.py"),
        "start": {"line": line},
        "extra": {
            "severity": severity,
            "message": f"Rule {check_id} fired",
            "lines": "some code here",
        },
    }


def test_semgrep_maps_severities_and_dedupes(tmp_path, fake_tools) -> None:
    (tmp_path / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    results = [
        _semgrep_result(tmp_path, "python.lang.security.audit.x", "ERROR", 10),
        _semgrep_result(tmp_path, "python.lang.security.audit.y", "WARNING", 20),
        _semgrep_result(tmp_path, "python.django.security.x", "ERROR", 30),
        _semgrep_result(tmp_path, "python.lang.security.audit.z", "INFO", 40),
    ]
    fake_tools(
        {"semgrep": _completed(json.dumps({"results": results}))},
        installed={"semgrep"},
    )
    findings, tools_used, _skipped = run_external_tools(tmp_path, [_native_finding("app.py", 10)])
    by_rule = {f.rule_id: f for f in findings}
    # Line 10 already has a native finding: dropped.
    assert "semgrep:python.lang.security.audit.x" not in by_rule
    # Django rule on a FastAPI app: dropped.
    assert "semgrep:python.django.security.x" not in by_rule
    # WARNING -> Medium, INFO -> Low.
    assert by_rule["semgrep:python.lang.security.audit.y"].severity == Severity.MEDIUM
    assert by_rule["semgrep:python.lang.security.audit.z"].severity == Severity.LOW
    assert by_rule["semgrep:python.lang.security.audit.y"].engine == FindingEngine.SEMGREP
    assert by_rule["semgrep:python.lang.security.audit.y"].start_line == 20
    assert "semgrep" in tools_used


def test_semgrep_timeout_is_skipped_not_fatal(tmp_path, fake_tools) -> None:
    fake_tools(
        {"semgrep": subprocess.TimeoutExpired(cmd=["semgrep"], timeout=120)},
        installed={"semgrep"},
    )
    findings, tools_used, skipped = run_external_tools(tmp_path, [])
    assert findings == []
    assert tools_used == ["native"]
    assert {s.tool: s.reason for s in skipped}["semgrep"] == "semgrep timed out"


def test_tools_not_installed_are_skipped(tmp_path, fake_tools) -> None:
    fake_tools({}, installed=set())
    findings, tools_used, skipped = run_external_tools(tmp_path, [])
    assert findings == []
    assert tools_used == ["native"]
    reasons = {s.tool: s.reason for s in skipped}
    assert reasons["semgrep"] == "semgrep is not installed"
    assert reasons["gitleaks"] == "gitleaks is not installed"
    assert reasons["osv-scanner"] == "osv-scanner is not installed"
    assert reasons["pip-audit"] == "pip-audit is not installed"


def test_semgrep_bad_json_is_skipped(tmp_path, fake_tools) -> None:
    fake_tools({"semgrep": _completed("not json at all")}, installed={"semgrep"})
    _, _, skipped = run_external_tools(tmp_path, [])
    reasons = {s.tool: s.reason for s in skipped}
    assert reasons["semgrep"] == "semgrep returned output that could not be read"


def test_gitleaks_finds_secret_in_history(tmp_path, fake_tools) -> None:
    (tmp_path / ".git").mkdir()
    leaks = [
        {
            "File": "app.py",
            "StartLine": 5,
            "RuleID": "generic-api-key",
            "Secret": "sk_live_abcdefgh12345678",  # gitleaks:allow
        },
        {
            # A bare secret with no known prefix must be masked too.
            "File": "config.py",
            "StartLine": 2,
            "RuleID": "generic-api-key",
            "Secret": "abcdefghijklmnop1234",  # gitleaks:allow
        },
    ]
    fake_tools(
        {"gitleaks": _completed(json.dumps(leaks), returncode=1)},
        installed={"gitleaks"},
    )
    findings, tools_used, _ = run_external_tools(tmp_path, [])
    assert len(findings) == 2
    finding = findings[0]
    assert finding.rule_id == "SECRET_GIT_HISTORY"
    assert finding.severity == Severity.CRITICAL
    assert finding.engine == FindingEngine.GITLEAKS
    assert finding.file == "app.py"
    assert finding.start_line == 5
    assert finding.snippet == "sk_l****"
    assert findings[1].snippet == "abcd****"
    assert "gitleaks" in tools_used


def test_gitleaks_skipped_without_git_dir(tmp_path, fake_tools) -> None:
    fake_tools({}, installed={"gitleaks"})
    _, _, skipped = run_external_tools(tmp_path, [])
    reasons = {s.tool: s.reason for s in skipped}
    assert reasons["gitleaks"] == "no .git directory in the upload"


def _osv_payload(tmp_path: Path) -> dict:
    return {
        "results": [
            {
                "source": {"path": str(tmp_path / "requirements.txt")},
                "packages": [
                    {
                        "package": {"name": "jinja2", "version": "3.1.5"},
                        "vulnerabilities": [
                            {
                                "id": "CVE-2024-1234",
                                "summary": "Example vuln",
                                "affected": [{"ranges": [{"events": [{"fixed": "3.1.6"}]}]}],
                            }
                        ],
                    },
                    {
                        # Transitive dep, not listed in requirements.txt.
                        "package": {"name": "markupsafe", "version": "2.0.1"},
                        "vulnerabilities": [{"id": "CVE-2024-9999"}],
                    },
                ],
            }
        ]
    }


def test_osv_scanner_maps_cve(tmp_path, fake_tools) -> None:
    (tmp_path / "requirements.txt").write_text("jinja2==3.1.5\nfastapi==0.115.6\n")
    fake_tools(
        {"osv-scanner": _completed(json.dumps(_osv_payload(tmp_path)), returncode=1)},
        installed={"osv-scanner"},
    )
    findings, tools_used, _ = run_external_tools(tmp_path, [])
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "CVE_DEP"
    assert finding.severity == Severity.MEDIUM
    assert finding.engine == FindingEngine.OSV
    assert finding.file == "requirements.txt"
    assert finding.start_line == 1
    assert finding.evidence.package is not None
    assert finding.evidence.package.name == "jinja2"
    assert finding.evidence.package.version == "3.1.5"
    assert finding.evidence.package.advisory == "CVE-2024-1234"
    assert finding.fix_guidance is not None
    assert "Fixed in 3.1.6." in finding.fix_guidance
    assert "osv-scanner" in tools_used


def test_pip_audit_fallback_when_osv_missing(tmp_path, fake_tools) -> None:
    (tmp_path / "requirements.txt").write_text("jinja2==3.1.5\n")
    payload = {
        "dependencies": [
            {
                "name": "jinja2",
                "version": "3.1.5",
                "vulns": [
                    {
                        "id": "CVE-2024-1234",
                        "fix_versions": ["3.1.6"],
                        "description": "Example vuln",
                    }
                ],
            }
        ]
    }
    fake_tools(
        {"pip-audit": _completed(json.dumps(payload), returncode=1)},
        installed={"pip-audit"},
    )
    findings, tools_used, skipped = run_external_tools(tmp_path, [])
    assert len(findings) == 1
    assert findings[0].rule_id == "CVE_DEP"
    assert findings[0].start_line == 1
    assert "pip-audit" in tools_used
    reasons = {s.tool: s.reason for s in skipped}
    assert reasons["osv-scanner"] == "osv-scanner is not installed"


def test_pip_audit_runs_with_no_deps_and_disable_pip(tmp_path, fake_tools) -> None:
    (tmp_path / "requirements.txt").write_text("jinja2==3.1.5\n")
    fake_run = fake_tools(
        {"pip-audit": _completed(json.dumps({"dependencies": []}))},
        installed={"pip-audit"},
    )
    run_external_tools(tmp_path, [])
    commands = [c for c in fake_run.commands if Path(c[0]).name == "pip-audit"]
    assert len(commands) == 1
    # pip-audit must never install or resolve the scanned project's packages.
    assert "--no-deps" in commands[0]
    assert "--disable-pip" in commands[0]


def test_cve_tools_skipped_without_manifests(tmp_path, fake_tools) -> None:
    fake_tools({}, installed={"osv-scanner", "pip-audit"})
    _, _, skipped = run_external_tools(tmp_path, [])
    reasons = {s.tool: s.reason for s in skipped}
    assert reasons["osv-scanner"] == "no requirements.txt or package.json found"
    assert reasons["pip-audit"] == "no requirements.txt found"


def test_scanners_run_with_minimal_env(tmp_path, monkeypatch) -> None:
    """Every scanner subprocess gets PATH and HOME only, nothing else.

    A marker var set in the server env must not reach the child, and the
    temp HOME handed to the child must exist while it runs and be gone
    once the scan returns.
    """
    seen_envs: list[dict[str, str]] = []
    homes_existed: list[bool] = []

    def _capture(command: list[str], **kwargs):
        env = kwargs["env"]
        seen_envs.append(env)
        homes_existed.append(Path(env["HOME"]).is_dir())
        return _completed(json.dumps({"results": []}))

    monkeypatch.setattr(external.subprocess, "run", _capture)
    monkeypatch.setattr(external, "find_tool", lambda name, tools_dir=None: f"/fake/{name}")
    monkeypatch.setenv("LAUNCHAUDIT_MARKER_SECRET", "do-not-leak")
    run_external_tools(tmp_path, [])
    assert seen_envs, "expected at least one scanner subprocess call"
    for env in seen_envs:
        assert set(env) == {"PATH", "HOME"}
        assert "LAUNCHAUDIT_MARKER_SECRET" not in env
        assert not Path(env["HOME"]).exists()
    assert all(homes_existed)


def test_run_passes_minimal_env_to_real_subprocess(monkeypatch) -> None:
    """The real _run path: a child process sees only PATH and HOME.

    Uses the `env` binary, which prints exactly the environment it was
    given (a Python child would add LC_CTYPE itself via locale coercion).
    """
    env_bin = shutil.which("env")
    if env_bin is None:
        pytest.skip("env binary is not available")
    monkeypatch.setenv("LAUNCHAUDIT_MARKER_SECRET", "do-not-leak")
    code, out, _err, timed_out = external._run([env_bin], timeout=30)
    assert not timed_out
    assert code == 0
    child_env = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    assert set(child_env) == {"PATH", "HOME"}
    assert "LAUNCHAUDIT_MARKER_SECRET" not in child_env
