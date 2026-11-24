"""Git history scanning: secrets left in old commits must be found.

The clone fetches full history (no --depth) so gitleaks sees old commits.
The end-to-end test needs real git + gitleaks binaries and skips when
either is missing (CI does not install gitleaks for the backend job).

Fake key-shaped values carry an inline `gitleaks:allow` comment.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from app.services.runs.code_input import clone_repo
from app.services.scan.external import _gitleaks_findings, find_tool

# Fake secret for tests only; not a real credential.
_LEAKED_KEY = "xK9mQ2vL8pR4tY7wN3bV6cZ1aS5dF8gH0jK2mN4p"  # gitleaks:allow


def _git(*args: str, cwd: Path) -> None:
    git = shutil.which("git")
    assert git is not None  # the test skips when git is missing
    subprocess.run(  # noqa: S603 - fixed local git command, no user input
        [
            git,
            "-c",
            "user.email=test@launchaudit.local",
            "-c",
            "user.name=LaunchAudit Test",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def test_clone_fetches_full_history(monkeypatch, tmp_path) -> None:
    """clone_repo must not pass --depth: history scanning needs old commits."""
    seen: dict[str, list[str]] = {}

    def _fake_run(command: list[str], **kwargs):
        seen["cmd"] = command
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="")

    monkeypatch.setattr("app.services.runs.code_input.subprocess.run", _fake_run)
    monkeypatch.setattr("app.services.runs.code_input.shutil.which", lambda name: "/usr/bin/git")
    clone_repo("https://github.com/example/demo.git", tmp_path / "demo")
    assert "--depth" not in seen["cmd"]
    assert "--single-branch" in seen["cmd"]


def test_secret_in_old_commit_is_found(tmp_path) -> None:
    """A secret removed at HEAD but present in an old commit is flagged."""
    if shutil.which("git") is None:
        pytest.skip("git is not installed")
    if find_tool("gitleaks") is None:
        pytest.skip("gitleaks is not installed")
    origin = tmp_path / "origin"
    origin.mkdir()
    _git("init", cwd=origin)
    (origin / "config.py").write_text(f'API_KEY = "{_LEAKED_KEY}"\n', encoding="utf-8")
    _git("add", "config.py", cwd=origin)
    _git("commit", "-m", "add config", cwd=origin)
    (origin / "config.py").unlink()
    (origin / "app.py").write_text('print("hello")\n', encoding="utf-8")
    _git("add", "-A", cwd=origin)
    _git("commit", "-m", "remove leaked config", cwd=origin)

    clone = tmp_path / "clone"
    clone_repo(str(origin), clone)
    findings, reason = _gitleaks_findings(clone, None)
    assert reason is None
    assert [f for f in findings if f.rule_id == "SECRET_GIT_HISTORY"], (
        f"expected a history secret finding, got {[(f.rule_id, f.file) for f in findings]}"
    )
