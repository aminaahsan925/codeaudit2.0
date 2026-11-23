"""Code scanning: native rules, vibe-coding checks, external tools.

`scan_tree(path)` is the entry point; it returns the run's code findings
in fix-first order. `run_code_scan(path)` also reports which tools ran
and which were skipped. `dedupe_findings(findings)` applies the run-wide
dedupe rules (tool findings at native locations, code CORS vs live CORS).
"""

from .dedupe import dedupe_findings, sort_findings
from .external import ToolSkipped, find_tool, run_external_tools
from .native import scan_native_files
from .runner import ScanLimitError, ScanOutcome, collect_files, run_code_scan, scan_tree
from .vibe import scan_vibe_files

__all__ = [
    "ScanLimitError",
    "ScanOutcome",
    "ToolSkipped",
    "collect_files",
    "dedupe_findings",
    "find_tool",
    "run_code_scan",
    "run_external_tools",
    "scan_native_files",
    "scan_tree",
    "scan_vibe_files",
    "sort_findings",
]
