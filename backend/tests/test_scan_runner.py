"""Tests for the scan runner: tree walk, limits, bundles, entry points."""

import os
from pathlib import Path

import pytest

from app.schemas.finding import FindingEngine
from app.services.scan import runner
from app.services.scan.rules import make_finding
from app.services.scan.runner import (
    ScanLimitError,
    collect_files,
    run_code_scan,
    scan_tree,
)

FIXTURE_LINE = 'API_KEY = "abcdefghijklmnop1234"\n'  # gitleaks:allow


@pytest.fixture(autouse=True)
def _no_real_external_tools(monkeypatch):
    """Runner tests never run real semgrep/gitleaks/osv (slow, networked).

    External-tool behaviour is covered by test_scan_external.py with
    mocked subprocess calls.
    """
    monkeypatch.setattr(runner, "run_external_tools", lambda *args, **kwargs: ([], ["native"], []))


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_scan_tree_finds_secret_and_sorts_fix_first(tmp_path) -> None:
    _write(tmp_path, "app.py", FIXTURE_LINE + "DEBUG = True\n")
    findings = scan_tree(tmp_path)
    assert [f.rule_id for f in findings] == ["SECRET_GENERIC", "DEBUG_MODE"]


def test_scan_tree_missing_path_returns_empty() -> None:
    assert scan_tree("/nonexistent/path/that/does/not/exist") == []


def test_scan_tree_wires_external_findings_in(tmp_path, monkeypatch) -> None:
    tool_finding = make_finding(
        rule_id="semgrep:python.lang.security",
        engine=FindingEngine.SEMGREP,
        file="app.py",
        start_line=9,
        snippet_text="x",
    )
    monkeypatch.setattr(
        runner,
        "run_external_tools",
        lambda *args, **kwargs: ([tool_finding], ["native", "semgrep"], []),
    )
    _write(tmp_path, "app.py", "DEBUG = True\n")
    outcome = run_code_scan(tmp_path)
    assert [f.rule_id for f in outcome.findings] == [
        "semgrep:python.lang.security",
        "DEBUG_MODE",
    ]
    assert outcome.tools_used == ["native", "vibe", "semgrep"]


def test_run_code_scan_without_external_reports_tools(tmp_path) -> None:
    _write(tmp_path, "app.py", "DEBUG = True\n")
    outcome = run_code_scan(tmp_path, run_external=False)
    assert outcome.tools_used == ["native", "vibe"]
    assert outcome.tools_skipped == []
    assert [f.rule_id for f in outcome.findings] == ["DEBUG_MODE"]


@pytest.mark.parametrize(
    "rel",
    [
        "node_modules/pkg/index.js",
        ".git/config",
        "venv/lib/x.py",
        ".venv/lib/x.py",
        "__pycache__/x.py",
        "dist/bundle.py",
        "build/out.py",
        ".env.example",
    ],
)
def test_skipped_paths_are_not_scanned(tmp_path, rel) -> None:
    _write(tmp_path, rel, FIXTURE_LINE)
    assert collect_files(tmp_path) == {}


def test_env_file_is_scanned_but_example_is_not(tmp_path) -> None:
    _write(tmp_path, ".env", "API_KEY=abcdefghijklmnop1234\n")  # gitleaks:allow
    _write(tmp_path, ".env.example", "API_KEY=abcdefghijklmnop1234\n")  # gitleaks:allow
    files = collect_files(tmp_path)
    assert list(files) == [".env"]


def test_minified_bundle_by_name_skipped(tmp_path) -> None:
    _write(tmp_path, "static/app.min.js", FIXTURE_LINE)
    _write(tmp_path, "static/app.bundle.js", FIXTURE_LINE)
    _write(tmp_path, "static/app.js", "const x = 1;\n")
    files = collect_files(tmp_path)
    assert list(files) == ["static/app.js"]


def test_minified_bundle_by_long_line_skipped(tmp_path) -> None:
    _write(tmp_path, "static/bundle.js", "x=" + "a" * 25_000 + "\n")
    _write(tmp_path, "static/app.js", "const x = 1;\n")
    files = collect_files(tmp_path)
    assert list(files) == ["static/app.js"]


def test_symlink_is_not_followed(tmp_path) -> None:
    target = _write(tmp_path, "real.py", FIXTURE_LINE)
    link = tmp_path / "link.py"
    os.symlink(target, link)
    files = collect_files(tmp_path)
    assert list(files) == ["real.py"]


def test_file_count_limit_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "MAX_TREE_FILES", 2)
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "b.py", "x = 1\n")
    _write(tmp_path, "c.py", "x = 1\n")
    with pytest.raises(ScanLimitError, match="exceeds 2 files"):
        collect_files(tmp_path)


def test_total_size_limit_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "MAX_TREE_BYTES", 10)
    _write(tmp_path, "a.py", "x = 1\n" + "y = 2\n" * 5)
    with pytest.raises(ScanLimitError, match="exceeds 10 bytes"):
        collect_files(tmp_path)


def test_oversized_single_file_is_skipped(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "MAX_FILE_BYTES", 10)
    _write(tmp_path, "big.py", FIXTURE_LINE)
    _write(tmp_path, "small.py", "x = 1\n")
    files = collect_files(tmp_path)
    assert list(files) == ["small.py"]


def test_binary_file_does_not_break_scan(tmp_path) -> None:
    (tmp_path / "data.txt").write_bytes(b"\x00\x01\x02\xff\xfe" * 100)
    _write(tmp_path, "app.py", "DEBUG = True\n")
    findings = scan_tree(tmp_path)
    assert [f.rule_id for f in findings] == ["DEBUG_MODE"]
