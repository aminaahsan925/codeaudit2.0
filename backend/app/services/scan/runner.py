"""Code scan runner: walk a tree, run native + vibe + external tools.

`scan_tree(path)` is the entry point: it returns the run's code findings
in fix-first order. `run_code_scan(path)` returns the same findings plus
which tools ran and which were skipped (and why).

Scanned code is read, never run, never imported. Symlinks are not
followed. Zip-bomb-style limits apply to the tree: max 50 MiB total,
max 2000 files, and files over 5 MiB are skipped.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.finding import Finding

from .dedupe import dedupe_findings
from .external import ToolSkipped, run_external_tools
from .native import scan_native_files
from .vibe import scan_vibe_files

# Zip-bomb-style limits for the scanned tree (same numbers as the zip
# extraction guard in PORTING-NOTES.md).
MAX_TREE_BYTES = 50 * 1024 * 1024  # 50 MiB total
MAX_TREE_FILES = 2000
MAX_FILE_BYTES = 5 * 1024 * 1024  # per-file cap; larger files are skipped

# A .js/.ts file whose longest line exceeds this is minified: a bundle,
# which belongs to the live checks, not the code scan.
MAX_SOURCE_LINE_CHARS = 20_000

SKIP_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
}

# Extensions the walker collects. Native rules use their own subset;
# vibe checks need .sql and .rules files as well.
SCAN_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".html",
    ".sql",
    ".rules",
}

BUNDLE_SUFFIXES = (".min.js", ".bundle.js", ".chunk.js")


class ScanLimitError(ValueError):
    """The scanned tree broke a size or file-count limit."""


@dataclass
class ScanOutcome:
    findings: list[Finding] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tools_skipped: list[ToolSkipped] = field(default_factory=list)


def _is_bundle(path: Path, lines: list[str]) -> bool:
    if path.name.endswith(BUNDLE_SUFFIXES):
        return True
    if path.suffix.lower() in {".js", ".ts", ".jsx", ".tsx"}:
        return any(len(line) > MAX_SOURCE_LINE_CHARS for line in lines)
    return False


def _is_scannable(path: Path) -> bool:
    if path.name == ".env.example":
        return False
    if path.name.startswith(".env"):
        return True
    return path.suffix.lower() in SCAN_EXTENSIONS


def collect_files(root: Path | str) -> dict[str, list[str]]:
    """Walk a tree and read its scannable files (rel_path -> lines).

    Raises ScanLimitError when the tree exceeds MAX_TREE_BYTES or
    MAX_TREE_FILES. Symlinks are skipped, never followed.
    """
    root = Path(root)
    files: dict[str, list[str]] = {}
    total_bytes = 0
    if not root.exists():
        return files
    # os.walk is lazy (limits bite during the walk, not after a full
    # traversal) and sorting each level keeps the result deterministic.
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not (Path(dirpath) / d).is_symlink()
        )
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            if not _is_scannable(path):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            total_bytes += size
            if total_bytes > MAX_TREE_BYTES:
                raise ScanLimitError(f"Scanned tree exceeds {MAX_TREE_BYTES} bytes total")
            if len(files) + 1 > MAX_TREE_FILES:
                raise ScanLimitError(f"Scanned tree exceeds {MAX_TREE_FILES} files")
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            lines = text.splitlines()
            if _is_bundle(path, lines):
                continue
            files[path.relative_to(root).as_posix()] = lines
    return files


def run_code_scan(
    path: Path | str,
    *,
    run_external: bool = True,
    tools_dir: Path | None = None,
) -> ScanOutcome:
    """Run the full code scan over a tree and report tools used/skipped."""
    root = Path(path)
    files = collect_files(root)
    native_findings = scan_native_files(files)
    vibe_findings = scan_vibe_files(files)
    findings = native_findings + vibe_findings
    tools_used = ["native", "vibe"]
    tools_skipped: list[ToolSkipped] = []
    if run_external:
        tool_findings, external_used, external_skipped = run_external_tools(
            root, native_findings, tools_dir
        )
        findings.extend(tool_findings)
        tools_used = ["native", "vibe"] + [tool for tool in external_used if tool != "native"]
        tools_skipped = external_skipped
    return ScanOutcome(
        findings=dedupe_findings(findings),
        tools_used=tools_used,
        tools_skipped=tools_skipped,
    )


def scan_tree(path: Path | str) -> list[Finding]:
    """Scan a directory tree. Returns the code findings, fix-first order."""
    return run_code_scan(path).findings
