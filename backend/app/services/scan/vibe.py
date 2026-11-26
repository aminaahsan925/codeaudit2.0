"""Vibe-coding checks (part of the code scan, engine "vibe").

The six narrow rules from CONTRACT.md, adapted from the old build's
vibe.py. These only fire on real Supabase / Firebase / Next.js / Vite /
browser-LLM patterns, so a plain FastAPI app is never flagged.
"""

import re
from pathlib import Path

from app.schemas.finding import Finding, FindingEngine

from .masking import (
    has_known_prefix,
    is_placeholder,
    is_secret_name,
    snippet,
)
from .rules import make_finding

FRONTEND_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx"}
FRONTEND_DIRS = {"src", "components", "pages", "app"}

SUPABASE_MARKERS = ("supabase-js", "SUPABASE_URL", "@supabase/")

CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE", re.IGNORECASE)
RLS_RE = re.compile(r"ENABLE\s+ROW\s+LEVEL\s+SECURITY|CREATE\s+POLICY", re.IGNORECASE)
SERVICE_KEY_RE = re.compile(r"SUPABASE_SERVICE_ROLE_KEY|service_role", re.IGNORECASE)
PUBLIC_VAR_RE = re.compile(
    r"""(?:NEXT_PUBLIC_|VITE_)([A-Za-z0-9_]*)\s*[:=]\s*["']?([^"'\s]+)["']?"""
)
FIREBASE_OPEN_RE = re.compile(
    r"allow\s+read,\s*write\s*:\s*if\s+true|"
    r"""["']\.read["']\s*:\s*true|["']\.write["']\s*:\s*true"""
)
API_HANDLER_RE = re.compile(
    r"export\s+(?:async\s+)?(?:function\s+|const\s+)(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b"
)
AUTH_CHECK_RE = re.compile(
    r"getSession|auth\s*\(|verifyToken|requireAuth|withAuth|"
    r"Authorization|getServerSession|currentUser"
)
LLM_KEY_RE = re.compile(r"OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|GROQ_API_KEY")
LLM_FETCH_RE = re.compile(
    r"api\.openai\.com|generativelanguage\.googleapis\.com|"
    r"api\.anthropic\.com|api\.groq\.com"
)
SK_KEY_RE = re.compile(r"sk-[A-Za-z0-9]{10,}")

FIREBASE_RULE_FILES = {"firestore.rules", "database.rules.json", "storage.rules"}
ENV_FILE_NAMES = {".env", ".env.local"}


def _is_frontend_file(rel_path: str) -> bool:
    path = Path(rel_path)
    if path.suffix.lower() in FRONTEND_EXTENSIONS:
        return True
    return any(part in FRONTEND_DIRS for part in path.parts)


def _is_api_route_file(rel_path: str) -> bool:
    path = Path(rel_path)
    if path.suffix.lower() not in FRONTEND_EXTENSIONS:
        return False
    return "api" in path.parts


def _looks_secret(value: str) -> bool:
    if len(value) < 12 or is_placeholder(value):
        return False
    if has_known_prefix(value):
        return True
    # A long, high-entropy-looking value in a public var.
    return bool(len(value) >= 20 and re.search(r"[A-Za-z]", value) and re.search(r"\d", value))


def _finding(rule_id: str, rel_path: str, lineno: int, line: str | None) -> Finding:
    return make_finding(
        rule_id=rule_id,
        engine=FindingEngine.VIBE,
        file=rel_path,
        start_line=lineno,
        snippet_text=snippet(line) if line else None,
    )


def _supabase_in_use(files: dict[str, list[str]]) -> bool:
    for rel_path, lines in files.items():
        if "migrations" in Path(rel_path).parts:
            return True
        for line in lines:
            if any(marker in line for marker in SUPABASE_MARKERS):
                return True
    return False


def scan_vibe_files(files: dict[str, list[str]]) -> list[Finding]:
    """Run the vibe checks over collected files (rel_path -> lines)."""
    findings: list[Finding] = []

    # Rule 1: Supabase tables without Row Level Security.
    if _supabase_in_use(files):
        for rel_path in sorted(files):
            lines = files[rel_path]
            is_sql = rel_path.endswith(".sql") or "migrations" in Path(rel_path).parts
            if not is_sql:
                continue
            whole = "\n".join(lines)
            if not CREATE_TABLE_RE.search(whole):
                continue
            if RLS_RE.search(whole):
                continue
            for lineno, line in enumerate(lines, start=1):
                if CREATE_TABLE_RE.search(line):
                    findings.append(_finding("SUPABASE_NO_RLS", rel_path, lineno, line))
                    break

    for rel_path in sorted(files):
        lines = files[rel_path]
        path = Path(rel_path)
        is_frontend = _is_frontend_file(rel_path)
        for lineno, line in enumerate(lines, start=1):
            # Rule 2: Supabase service-role key in frontend code.
            if is_frontend and SERVICE_KEY_RE.search(line):
                findings.append(_finding("SUPABASE_SERVICE_KEY_FRONTEND", rel_path, lineno, line))

            # Rule 3: secrets in NEXT_PUBLIC_ or VITE_ variables. Only
            # secret-like values are flagged (CONTRACT.md rule 1/2
            # patterns); public vars with ordinary values are not.
            if path.name in ENV_FILE_NAMES or is_frontend:
                match = PUBLIC_VAR_RE.search(line)
                if match:
                    var_name, value = match.group(1), match.group(2)
                    secret_like = (
                        has_known_prefix(value)
                        or (len(value) >= 12 and is_secret_name(var_name))
                        or _looks_secret(value)
                    )
                    if secret_like and not is_placeholder(value):
                        findings.append(_finding("SECRET_IN_PUBLIC_VAR", rel_path, lineno, line))

            # Rule 6: LLM API key called from the browser. A fetch to an
            # LLM API from frontend code, the key name in a browser file,
            # or a bare sk- key in a browser file all count.
            if is_frontend and (
                LLM_KEY_RE.search(line) or LLM_FETCH_RE.search(line) or SK_KEY_RE.search(line)
            ):
                findings.append(_finding("LLM_KEY_FROM_BROWSER", rel_path, lineno, line))

    # Rule 4: open Firebase rules (one finding per file).
    for rel_path in sorted(files):
        if Path(rel_path).name not in FIREBASE_RULE_FILES:
            continue
        for lineno, line in enumerate(files[rel_path], start=1):
            if FIREBASE_OPEN_RE.search(line):
                findings.append(_finding("FIREBASE_OPEN_RULES", rel_path, lineno, line))
                break

    # Rule 5: API route handler with no auth check (JS/TS only).
    for rel_path in sorted(files):
        if not _is_api_route_file(rel_path):
            continue
        lines = files[rel_path]
        whole = "\n".join(lines)
        if not API_HANDLER_RE.search(whole):
            continue
        if AUTH_CHECK_RE.search(whole):
            continue
        for lineno, line in enumerate(lines, start=1):
            if API_HANDLER_RE.search(line):
                findings.append(_finding("API_ROUTE_NO_AUTH", rel_path, lineno, line))
                break

    return findings
