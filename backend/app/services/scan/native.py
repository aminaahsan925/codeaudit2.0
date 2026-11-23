"""Native code scan rules (always run).

The ten rules from CONTRACT.md, adapted from the old build's scan.py.
Every finding has file + line + masked snippet, and a best-effort data-flow
trace for the injection rules when a request-sourced variable is involved.

No-flag cases (verified by tests): env reads, placeholder values,
parameterized queries (? / %s placeholders), string literals passed to
os.system/eval/exec, hashlib.sha256 and secrets.*.
"""

import re
from pathlib import Path

from app.schemas.finding import Confidence, Evidence, Finding, FindingEngine, TraceStep

from .masking import (
    ASSIGNMENT_RE,
    has_known_prefix,
    is_env_read,
    is_placeholder,
    is_secret_name,
    snippet,
)
from .rules import make_finding

NATIVE_EXTENSIONS = {
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
}

# Rule 3: password length check with a minimum below 8.
LEN_PASSWORD_RE = re.compile(r"len\s*\([^)]*password[^)]*\)\s*<\s*(\d+)", re.IGNORECASE)
LENGTH_PASSWORD_RE = re.compile(r"password\w*\.length\s*<\s*(\d+)", re.IGNORECASE)

# Rule 4: debug mode on.
DEBUG_RES = [
    re.compile(r"\bdebug\s*=\s*True\b", re.IGNORECASE),
    re.compile(r"\bdebug\s*:\s*true\b", re.IGNORECASE),
    re.compile(r"app\.run\([^)]*debug\s*=\s*True", re.IGNORECASE),
]

# Rule 5: CORS wildcard.
CORS_RES = [
    re.compile(r"""allow_origins\s*=\s*\[\s*["']\*["']\s*\]"""),
    re.compile(r"""Access-Control-Allow-Origin["']?\s*:\s*\*"""),
]

# Rule 1 (unquoted): bare assignments as in .env and YAML files. Anchored
# to the start of the line so a token inside a quoted string on a code line
# (e.g. a URL query param) is never mistaken for an assignment.
UNQUOTED_LINE_RE = re.compile(
    r"""^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*[:=]\s*([^\s"'#]{12,})"""
)

# Rule 10: hardcoded password assignment, 8+ chars.
PASSWORD_ASSIGN_RE = re.compile(
    r"""\b(passw(or)?d|passwd)\b\s*=\s*["']([^"']{8,})["']""", re.IGNORECASE
)

# Rule 6: SQL injection. A SQL keyword plus a "built string" pattern on the
# same line, together with a sink, is the signal. Parameterized queries
# (?, %s placeholders passed as a separate argument) match none of the
# built-string patterns, so they are never flagged.
SQL_KEYWORD_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|WITH)\b", re.IGNORECASE)
SQL_SINK_RE = re.compile(r"\.\s*(execute|executemany|query|raw)\s*\(")
SQL_FSTRING_RE = re.compile(r"""[fF](?:"[^"]*\{|'[^']*\{)""")
SQL_FORMAT_RE = re.compile(r"""["']\s*%\s*[A-Za-z_(]""")
SQL_DOTFORMAT_RE = re.compile(r"""\.format\s*\(""")
SQL_CONCAT_RE = re.compile(r"""["']\s*\+\s*[A-Za-z_]""")
SQL_CONCAT_REV_RE = re.compile(r"""[A-Za-z_][A-Za-z0-9_]*\s*\+\s*["']""")
SQL_ASSIGN_RE = re.compile(r"""^[\s]*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*""")

# Rule 7: XSS. Only when the value is a variable, not a string literal.
INNERHTML_RE = re.compile(r"\.innerHTML\s*=\s*(?![\"'`])\s*[A-Za-z_]")
DOCUMENT_WRITE_RE = re.compile(r"document\.write\s*\(\s*(?![\"'`])\s*[A-Za-z_]")
DANGEROUS_HTML_RE = re.compile(
    r"dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*(?![\"'`])\s*[A-Za-z_]"
)
JINJA_SAFE_RE = re.compile(r"\{\{\s*[A-Za-z_][A-Za-z0-9_.| ]*\|\s*safe\s*\}\}")
RENDER_TEMPLATE_STRING_RE = re.compile(
    r"render_template_string\s*\(\s*(?:[fF][\"'][^\"']*\{|(?![\"'`])[A-Za-z_])"
)

# Rule 8: command injection. Literals only (no variable) are NOT flagged.
OS_SYSTEM_RE = re.compile(r"os\.(?:system|popen)\s*\(\s*(?![\"'`])\s*[A-Za-z_]")
SUBPROCESS_SHELL_RE = re.compile(
    r"subprocess\.\w+\s*\(\s*(?![\"'`][^\"'`]*[\"'`]\s*,\s*[^,]*shell\s*=\s*True)"
    r"[^)]*shell\s*=\s*True"
)
EVAL_EXEC_RE = re.compile(r"\b(?:eval|exec)\s*\(\s*(?![\"'`])\s*[A-Za-z_]")

# Rule 9: weak crypto. hashlib.sha256 and secrets.* are NOT flagged.
WEAK_HASH_RE = re.compile(r"hashlib\.(?:md5|sha1)\s*\(")
WEAK_CIPHER_RE = re.compile(r"Crypto\.Cipher\.(?:DES3?|ARC4)\b|ARC4\.new\s*\(")
WEAK_RANDOM_RE = re.compile(r"(?:random\.random|Math\.random)\s*\(")
TOKEN_WORD_RE = re.compile(r"token|secret|password|api[_-]?key", re.IGNORECASE)

# Request data sources, for best-effort taint traces.
REQUEST_SOURCE_RE = re.compile(
    r"(request\.(?:form|args|json|data|values|cookies)|"
    r"req\.(?:body|query|params)|input\s*\()"
)
REQUEST_ASSIGN_RE = re.compile(
    r"""^[\s]*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*.*"""
    r"(request\.(?:form|args|json|data|values|cookies)|"
    r"req\.(?:body|query|params)|input\s*\()"
)


def _is_built_sql(line: str) -> bool:
    """True when the line builds a SQL string from a variable."""
    if not SQL_KEYWORD_RE.search(line):
        return False
    return bool(
        SQL_FSTRING_RE.search(line)
        or SQL_FORMAT_RE.search(line)
        or SQL_DOTFORMAT_RE.search(line)
        or SQL_CONCAT_RE.search(line)
        or SQL_CONCAT_REV_RE.search(line)
    )


class _FileContext:
    """Per-file state: request-sourced variables and built SQL strings."""

    def __init__(self, lines: list[str]):
        self.lines = lines
        # Variable name -> line number where request data was assigned to it.
        self.request_vars: dict[str, int] = {}
        self.built_sql_vars: set[str] = set()
        for lineno, line in enumerate(lines, start=1):
            match = REQUEST_ASSIGN_RE.match(line)
            if match:
                self.request_vars.setdefault(match.group(1), lineno)
            if _is_built_sql(line):
                match = SQL_ASSIGN_RE.match(line)
                if match:
                    self.built_sql_vars.add(match.group(1))

    def trace_for(self, line: str, rel_path: str, lineno: int) -> tuple[list[TraceStep], Evidence]:
        """Best-effort taint trace when a request-sourced variable is used.

        Returns (trace steps, evidence). When the variable traces to a
        request assignment in the same file, the trace has a source step
        and a sink step; otherwise the trace is empty and the path string
        goes in evidence.notes.
        """
        for var in sorted(self.request_vars):
            if re.search(rf"\b{re.escape(var)}\b", line):
                source_line = self.request_vars[var]
                return [
                    TraceStep(
                        file=rel_path,
                        line=source_line,
                        snippet=snippet(self.lines[source_line - 1]),
                        label="Request data enters here",
                    ),
                    TraceStep(
                        file=rel_path,
                        line=lineno,
                        snippet=snippet(line),
                        label=f"Flows through {var} into a sink",
                    ),
                ], Evidence()
        if REQUEST_SOURCE_RE.search(line):
            return [], Evidence(notes="request data -> sink")
        return [], Evidence()


def _is_native_file(rel_path: str) -> bool:
    path = Path(rel_path)
    if path.name.startswith(".env"):
        return True
    return path.suffix.lower() in NATIVE_EXTENSIONS


def _allows_bare_assignments(rel_path: str) -> bool:
    """True for files where values are written without quotes.

    In .env, YAML, and plain-text files a bare `NAME=value` line is a
    literal value. In code files it is an expression (`token = get_it()`),
    so the unquoted secret check must not run there.
    """
    path = Path(rel_path)
    if path.name.startswith(".env"):
        return True
    return path.suffix.lower() in {".yml", ".yaml", ".txt"}


def _scan_line(
    line: str,
    rel_path: str,
    lineno: int,
    ctx: _FileContext,
    *,
    bare_assignments: bool,
) -> list[Finding]:
    """Return the findings for one line, applying the dedupe rules."""
    findings: list[Finding] = []
    fired: set[str] = set()

    def add(
        rule_id: str,
        *,
        trace: list[TraceStep] | None = None,
        evidence: Evidence | None = None,
        confidence: Confidence | None = None,
    ) -> None:
        findings.append(
            make_finding(
                rule_id=rule_id,
                engine=FindingEngine.NATIVE,
                file=rel_path,
                start_line=lineno,
                snippet_text=snippet(line),
                trace=trace,
                evidence=evidence,
                confidence=confidence,
            )
        )
        fired.add(rule_id)

    # Rule 2 first: a known key format suppresses SECRET_GENERIC on the line.
    if has_known_prefix(line):
        add("SECRET_KNOWN_PREFIX")

    # Rule 1: secret-like name assigned a string value of 12+ chars.
    # Quoted assignments (code, JSON) and unquoted ones (.env, YAML).
    if "SECRET_KNOWN_PREFIX" not in fired and not is_env_read(line):
        secret_found = False
        for match in ASSIGNMENT_RE.finditer(line):
            name, value = match.group(1), match.group(2)
            if len(value) < 12:
                continue
            if not is_secret_name(name):
                continue
            if is_placeholder(value):
                continue
            secret_found = True
            break
        if not secret_found and bare_assignments:
            match = UNQUOTED_LINE_RE.match(line)
            if match and is_secret_name(match.group(1)) and not is_placeholder(match.group(2)):
                secret_found = True
        if secret_found:
            add("SECRET_GENERIC")

    # Rule 10: hardcoded password, 8+ chars. Suppressed if rule 1 fired.
    if "SECRET_GENERIC" not in fired and not is_env_read(line):
        match = PASSWORD_ASSIGN_RE.search(line)
        if match and not is_placeholder(match.group(3)):
            add("HARDCODED_CREDENTIAL")

    # Rule 3: weak password rule (minimum below 8).
    weak = False
    for pattern in (LEN_PASSWORD_RE, LENGTH_PASSWORD_RE):
        match = pattern.search(line)
        if match and int(match.group(1)) < 8:
            weak = True
            break
    if weak:
        add("WEAK_PASSWORD_RULE")

    # Rule 4: debug mode on.
    if any(pattern.search(line) for pattern in DEBUG_RES):
        add("DEBUG_MODE")

    # Rule 5: CORS wildcard.
    if any(pattern.search(line) for pattern in CORS_RES):
        add("CORS_WILDCARD")

    # Rule 6: SQL injection. Only when a sink is on the same statement
    # or a built SQL string is passed to one.
    if SQL_SINK_RE.search(line):
        built = _is_built_sql(line)
        sink_var = None
        if not built:
            for var in ctx.built_sql_vars:
                if re.search(rf"\b{re.escape(var)}\b", line):
                    sink_var = var
                    break
        if built or sink_var:
            trace, evidence = ctx.trace_for(line, rel_path, lineno)
            add(
                "SQL_INJECTION",
                trace=trace,
                evidence=evidence,
                confidence=Confidence.HIGH if trace else None,
            )

    # Rule 7: XSS. Only when the value is a variable, not a literal.
    xss = bool(
        INNERHTML_RE.search(line)
        or DOCUMENT_WRITE_RE.search(line)
        or DANGEROUS_HTML_RE.search(line)
        or JINJA_SAFE_RE.search(line)
        or RENDER_TEMPLATE_STRING_RE.search(line)
    )
    if xss:
        trace, evidence = ctx.trace_for(line, rel_path, lineno)
        add(
            "XSS",
            trace=trace,
            evidence=evidence,
            confidence=Confidence.HIGH if trace else None,
        )

    # Rule 8: command injection. Literals only are NOT flagged.
    cmd = bool(
        OS_SYSTEM_RE.search(line) or EVAL_EXEC_RE.search(line) or SUBPROCESS_SHELL_RE.search(line)
    )
    if cmd:
        trace, evidence = ctx.trace_for(line, rel_path, lineno)
        add(
            "COMMAND_INJECTION",
            trace=trace,
            evidence=evidence,
            confidence=Confidence.HIGH if trace else None,
        )

    # Rule 9: weak crypto. hashlib.sha256 and secrets.* are NOT flagged.
    weak_crypto = bool(
        WEAK_HASH_RE.search(line)
        or WEAK_CIPHER_RE.search(line)
        or (WEAK_RANDOM_RE.search(line) and TOKEN_WORD_RE.search(line))
    )
    if weak_crypto:
        add("WEAK_CRYPTO")

    return findings


def scan_native_files(files: dict[str, list[str]]) -> list[Finding]:
    """Run the native rules over collected files (rel_path -> lines)."""
    findings: list[Finding] = []
    for rel_path in sorted(files):
        if not _is_native_file(rel_path):
            continue
        lines = files[rel_path]
        ctx = _FileContext(lines)
        bare = _allows_bare_assignments(rel_path)
        for lineno, line in enumerate(lines, start=1):
            findings.extend(_scan_line(line, rel_path, lineno, ctx, bare_assignments=bare))
    return findings
