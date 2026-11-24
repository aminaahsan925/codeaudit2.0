"""Optional external scanners: semgrep, gitleaks, osv-scanner / pip-audit.

Best effort, never required. Native rules always run; these tools only
add findings when they are installed and succeed. A tool failing or
timing out never fails the audit; it is recorded as skipped.

Binaries are looked up on PATH first, then in backend/tools/ (release
binaries downloaded there), then in backend/.venv/bin.
"""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.schemas.finding import (
    Evidence,
    Finding,
    FindingEngine,
    PackageEvidence,
    Severity,
)

from .masking import mask_secret, mask_text
from .rules import make_finding

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DIR = BASE_DIR / "tools"
VENV_BIN = BASE_DIR / ".venv" / "bin"

SEMGREP_TIMEOUT = 120
GITLEAKS_TIMEOUT = 120
CVE_TIMEOUT = 180

SEMGREP_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "ERROR": Severity.HIGH,
    "WARNING": Severity.MEDIUM,
    "INFO": Severity.LOW,
}

# Semgrep rules tied to a specific framework. A Django rule firing on a
# FastAPI app (semgrep mistakes Jinja2 templates for Django templates)
# is a false positive, so framework rules are dropped when the framework
# is not actually used by the scanned project.
FRAMEWORK_RULE_PREFIXES = {
    "python.django.": "django",
    "python.flask.": "flask",
}
FRAMEWORK_MARKERS = {
    "django": (
        re.compile(r"^\s*(?:import\s+django|from\s+django\b)", re.MULTILINE),
        re.compile(r"(?m)^django\s*[=<>~!]", re.IGNORECASE),
        re.compile(r'"django"\s*:', re.IGNORECASE),
    ),
    "flask": (
        re.compile(r"^\s*(?:import\s+flask|from\s+flask\b)", re.MULTILINE),
        re.compile(r"(?m)^flask\s*[=<>~!]", re.IGNORECASE),
        re.compile(r'"flask"\s*:', re.IGNORECASE),
    ),
}


@dataclass
class ToolSkipped:
    tool: str
    reason: str


def find_tool(name: str, tools_dir: Path | None = None) -> str | None:
    """Locate a scanner binary: PATH, backend/tools/, then .venv/bin."""
    found = shutil.which(name)
    if found:
        return found
    search_dir = tools_dir or TOOLS_DIR
    for candidate in (search_dir / name, VENV_BIN / name):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _run(
    command: list[str], timeout: int, cwd: Path | None = None
) -> tuple[int | None, str, str, bool]:
    """Run a scanner. Returns (returncode, stdout, stderr, timed_out)."""
    try:
        # The command is a resolved tool binary plus fixed flags; the
        # scanned tree path is one argument, never a shell command
        # (shell=False), so it cannot inject anything.
        proc = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            shell=False,
        )
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired:
        return None, "", "timed out", True
    except OSError as exc:
        return None, "", str(exc), False


def _detect_frameworks(tree: Path) -> set[str]:
    """Frameworks actually used by the project (django, flask)."""
    found: set[str] = set()
    manifest_names = {
        "requirements.txt",
        "requirements-dev.txt",
        "Pipfile",
        "pyproject.toml",
        "setup.py",
        "package.json",
    }
    texts = []
    for path in sorted(tree.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.lower() == ".py" or path.name in manifest_names:
            try:
                texts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    combined = "\n".join(texts)
    for framework, markers in FRAMEWORK_MARKERS.items():
        if any(marker.search(combined) for marker in markers):
            found.add(framework)
    return found


def _relative_path(tree: Path, path: str) -> str:
    try:
        return Path(path).resolve().relative_to(tree.resolve()).as_posix()
    except ValueError:
        return os.path.basename(path)


def _semgrep_findings(
    tree: Path, native_locations: set, tools_dir: Path | None
) -> tuple[list[Finding], str | None]:
    """Run semgrep --config auto --json. Returns (findings, skip_reason)."""
    binary = find_tool("semgrep", tools_dir)
    if binary is None:
        return [], "semgrep is not installed"
    code, out, err, timed_out = _run(
        [binary, "--config", "auto", "--json", "--quiet", str(tree)],
        timeout=SEMGREP_TIMEOUT,
    )
    if timed_out:
        return [], "semgrep timed out"
    if code is None:
        return [], f"semgrep could not run: {err[:200]}"
    try:
        data = json.loads(out)
    except ValueError:
        return [], "semgrep returned output that could not be read"
    frameworks = _detect_frameworks(tree)
    findings: list[Finding] = []
    for result in data.get("results", []):
        check_id = str(result.get("check_id", "unknown"))
        if any(
            check_id.startswith(prefix) and framework not in frameworks
            for prefix, framework in FRAMEWORK_RULE_PREFIXES.items()
        ):
            continue
        rel = _relative_path(tree, result.get("path", ""))
        line = result.get("start", {}).get("line")
        if (rel, line) in native_locations:
            continue
        extra = result.get("extra", {}) or {}
        severity = SEMGREP_SEVERITY.get(str(extra.get("severity", "")).upper(), Severity.MEDIUM)
        message = (extra.get("message") or "").strip()
        snippet_lines = extra.get("lines") or ""
        findings.append(
            make_finding(
                rule_id="semgrep:" + check_id,
                engine=FindingEngine.SEMGREP,
                file=rel,
                start_line=line,
                snippet_text=mask_text(snippet_lines.strip())[:500] or None,
                title=message[:120] or "Semgrep finding",
                severity=severity,
            )
        )
    return findings, None


def _gitleaks_findings(tree: Path, tools_dir: Path | None) -> tuple[list[Finding], str | None]:
    """Run gitleaks for secrets in git history. Returns (findings, reason)."""
    binary = find_tool("gitleaks", tools_dir)
    if binary is None:
        return [], "gitleaks is not installed"
    if not (tree / ".git").exists():
        return [], "no .git directory in the upload"
    code, out, err, timed_out = _run(
        [
            binary,
            "detect",
            "--source",
            str(tree),
            "--report-format",
            "json",
            "--report-path",
            "-",
        ],
        timeout=GITLEAKS_TIMEOUT,
    )
    if timed_out:
        return [], "gitleaks timed out"
    if code is None:
        return [], f"gitleaks could not run: {err[:200]}"
    # gitleaks exits 1 when leaks are found; that is a success for us.
    try:
        data = json.loads(out) if out.strip() else []
    except ValueError:
        return [], "gitleaks returned output that could not be read"
    findings: list[Finding] = []
    seen: set[tuple] = set()
    for leak in data:
        rel = leak.get("File", "")
        line = leak.get("StartLine")
        key = (rel, line, leak.get("RuleID"))
        if key in seen:
            continue
        seen.add(key)
        secret = leak.get("Secret", "")
        findings.append(
            make_finding(
                rule_id="SECRET_GIT_HISTORY",
                engine=FindingEngine.GITLEAKS,
                file=rel or None,
                start_line=line,
                # The Secret field IS the secret value, so mask it
                # directly; mask_text only masks secrets inside code.
                snippet_text=mask_secret(secret) if secret else None,
                evidence=Evidence(notes=f"Gitleaks rule: {leak.get('RuleID', 'secret')}"),
            )
        )
    return findings, None


def _cve_finding(
    pkg_name: str,
    pkg_version: str,
    vuln_id: str,
    fixed: str,
    rel: str,
    line: int,
    summary: str,
) -> Finding:
    how_extra = f"Fixed in {fixed}." if fixed else None
    notes = f"{pkg_name} has a known vulnerability, {vuln_id}."
    if summary:
        notes += f" {summary[:200]}"
    return make_finding(
        rule_id="CVE_DEP",
        engine=FindingEngine.OSV,
        file=rel,
        start_line=line,
        title=f"Dependency with a known vulnerability: {pkg_name}",
        evidence=Evidence(
            package=PackageEvidence(name=pkg_name, version=pkg_version, advisory=vuln_id),
            notes=notes,
        ),
        how_extra=how_extra,
    )


def _fixed_version(vuln: dict) -> str:
    for affected in vuln.get("affected", []) or []:
        for event in (affected.get("ranges") or [{}])[0].get("events", []) or []:
            if "fixed" in event:
                return str(event["fixed"])
    return ""


def _find_dep_line(manifest_file: Path, pkg_name: str) -> int | None:
    """Best-effort line number of a package in a manifest file.

    Handles requirements.txt lines (name==version, name>=version, name)
    and package.json lines ("name": "version"). Returns None when the
    package is not listed (e.g. a transitive dependency).
    """
    if not pkg_name:
        return None
    try:
        lines = manifest_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    normalized = pkg_name.lower().replace("_", "-")
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip().rstrip(",").strip()
        if not stripped or stripped.startswith(("#", "{", "}", "[", "]")):
            continue
        candidate = stripped.strip('"').strip("'")
        base = re.split(r"[=:<>~!; \t]", candidate, maxsplit=1)[0].strip().strip('"').strip("'")
        if base.lower().replace("_", "-") == normalized:
            return lineno
    return None


def _cve_findings_osv(tree: Path, tools_dir: Path | None) -> tuple[list[Finding], str | None]:
    """Run osv-scanner on requirements.txt / package.json."""
    binary = find_tool("osv-scanner", tools_dir)
    if binary is None:
        return [], "osv-scanner is not installed"
    targets = [str(p) for p in (tree / "requirements.txt", tree / "package.json") if p.is_file()]
    if not targets:
        return [], "no requirements.txt or package.json found"
    code, out, err, timed_out = _run(
        [binary, "--format", "json", *targets],
        timeout=CVE_TIMEOUT,
    )
    if timed_out:
        return [], "osv-scanner timed out"
    if code is None:
        return [], f"osv-scanner could not run: {err[:200]}"
    # osv-scanner exits 1 when vulnerabilities are found.
    try:
        data = json.loads(out) if out.strip() else {}
    except ValueError:
        return [], "osv-scanner returned output that could not be read"
    findings: list[Finding] = []
    seen: set[tuple] = set()
    for result in data.get("results", []):
        source_path = result.get("source", {}).get("path", "")
        try:
            rel = Path(source_path).relative_to(tree).as_posix()
        except ValueError:
            rel = os.path.basename(source_path) or "requirements.txt"
        for package in result.get("packages", []):
            pkg = package.get("package", {}) or {}
            pkg_name = pkg.get("name", "")
            pkg_version = str(pkg.get("version", ""))
            line = _find_dep_line(tree / rel, pkg_name)
            if line is None:
                # Transitive dependency: not listed in the manifest, so
                # there is no file:line for the finding and no pin the
                # user can bump directly. Skip it.
                continue
            for vuln in package.get("vulnerabilities", []):
                vuln_id = vuln.get("id", "")
                key = (pkg_name, vuln_id)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    _cve_finding(
                        pkg_name,
                        pkg_version,
                        vuln_id,
                        _fixed_version(vuln),
                        rel,
                        line,
                        vuln.get("summary", ""),
                    )
                )
    return findings, None


def _cve_findings_pip_audit(tree: Path, tools_dir: Path | None) -> tuple[list[Finding], str | None]:
    """Run pip-audit on requirements.txt (fallback when osv is absent)."""
    binary = find_tool("pip-audit", tools_dir)
    if binary is None:
        return [], "pip-audit is not installed"
    req_file = tree / "requirements.txt"
    if not req_file.is_file():
        return [], "no requirements.txt found"
    code, out, err, timed_out = _run(
        [
            binary,
            "-r",
            str(req_file),
            "--format",
            "json",
            "--progress-spinner",
            "off",
            "--no-deps",
            "--disable-pip",
        ],
        timeout=CVE_TIMEOUT,
    )
    if timed_out:
        return [], "pip-audit timed out"
    if code is None:
        return [], f"pip-audit could not run: {err[:200]}"
    try:
        data = json.loads(out) if out.strip() else {}
    except ValueError:
        return [], "pip-audit returned output that could not be read"
    findings: list[Finding] = []
    seen: set[tuple] = set()
    for dep in data.get("dependencies", []):
        pkg_name = dep.get("name", "")
        pkg_version = str(dep.get("version", ""))
        line = _find_dep_line(req_file, pkg_name)
        if line is None:
            # Transitive dependency: not listed in requirements.txt, so
            # there is no file:line for the finding and no pin the user
            # can bump directly. Skip it.
            continue
        for vuln in dep.get("vulns", []):
            vuln_id = vuln.get("id", "")
            key = (pkg_name, vuln_id)
            if key in seen:
                continue
            seen.add(key)
            fix_versions = vuln.get("fix_versions") or []
            fixed = str(fix_versions[0]) if fix_versions else ""
            findings.append(
                _cve_finding(
                    pkg_name,
                    pkg_version,
                    vuln_id,
                    fixed,
                    "requirements.txt",
                    line,
                    vuln.get("description", ""),
                )
            )
    return findings, None


def run_external_tools(
    tree: Path | str,
    native_findings: list[Finding],
    tools_dir: Path | None = None,
) -> tuple[list[Finding], list[str], list[ToolSkipped]]:
    """Run every optional tool that is available.

    Returns (findings, tools_used, tools_skipped). tools_used always
    includes "native". tools_skipped is a list of ToolSkipped.
    """
    tree = Path(tree)
    native_locations = {(f.file, f.start_line) for f in native_findings}
    findings: list[Finding] = []
    tools_used = ["native"]
    tools_skipped: list[ToolSkipped] = []

    semgrep_findings, reason = _semgrep_findings(tree, native_locations, tools_dir)
    if reason is None:
        tools_used.append("semgrep")
        findings.extend(semgrep_findings)
    else:
        tools_skipped.append(ToolSkipped(tool="semgrep", reason=reason))

    gitleaks_findings, reason = _gitleaks_findings(tree, tools_dir)
    if reason is None:
        tools_used.append("gitleaks")
        findings.extend(gitleaks_findings)
    else:
        tools_skipped.append(ToolSkipped(tool="gitleaks", reason=reason))

    cve_findings, reason = _cve_findings_osv(tree, tools_dir)
    if reason is None:
        tools_used.append("osv-scanner")
        findings.extend(cve_findings)
    else:
        tools_skipped.append(ToolSkipped(tool="osv-scanner", reason=reason))
        cve_findings, reason = _cve_findings_pip_audit(tree, tools_dir)
        if reason is None:
            tools_used.append("pip-audit")
            findings.extend(cve_findings)
        else:
            tools_skipped.append(ToolSkipped(tool="pip-audit", reason=reason))

    return findings, tools_used, tools_skipped
