"""Rule metadata for the code scanner and the Finding factory.

Every rule carries its severity, category, confidence, title, why-it-matters
text and how-to-fix text in one place, so every finding gets consistent
fix_guidance (Markdown: "Why it matters" then "How to fix").
"""

import uuid
from dataclasses import dataclass

from app.schemas.finding import (
    Confidence,
    Evidence,
    Finding,
    FindingCategory,
    FindingEngine,
    Severity,
    TraceStep,
)

GENERIC_WHY = "A static analysis rule flagged this code as a known risky pattern."
GENERIC_FIX = "Fix this before launch, then run the check again to confirm it is gone."


@dataclass(frozen=True)
class RuleMeta:
    severity: Severity
    category: FindingCategory
    confidence: Confidence
    title: str
    why_it_matters: str
    how_to_fix: str
    cwe: str | None = None


RULES: dict[str, RuleMeta] = {
    "SECRET_GENERIC": RuleMeta(
        severity=Severity.CRITICAL,
        category=FindingCategory.SECRETS,
        confidence=Confidence.MEDIUM,
        title="Secret value in code",
        why_it_matters=(
            "A leaked secret lets strangers act as your app: read customer "
            "data, send messages, or spend your money."
        ),
        how_to_fix=(
            "Move the key to an environment variable, remove it from the "
            "code and commit history, then rotate it."
        ),
        cwe="CWE-798",
    ),
    "SECRET_KNOWN_PREFIX": RuleMeta(
        severity=Severity.CRITICAL,
        category=FindingCategory.SECRETS,
        confidence=Confidence.HIGH,
        title="Known secret key format in code",
        why_it_matters=(
            "Anyone with the code can use this key as if they were you, "
            "and run up bills or read your data."
        ),
        how_to_fix=(
            "This key format looks real, so treat it as exposed. Move it "
            "to an environment variable and rotate it right away."
        ),
        cwe="CWE-798",
    ),
    "HARDCODED_CREDENTIAL": RuleMeta(
        severity=Severity.CRITICAL,
        category=FindingCategory.SECRETS,
        confidence=Confidence.MEDIUM,
        title="Hardcoded password in code",
        why_it_matters=(
            "A password in code is a password anyone can find, and it "
            "stays in the history even after you delete it."
        ),
        how_to_fix=(
            "Move the password to an environment variable or a secrets "
            "manager and change the password."
        ),
        cwe="CWE-798",
    ),
    "SECRET_GIT_HISTORY": RuleMeta(
        severity=Severity.CRITICAL,
        category=FindingCategory.SECRETS,
        confidence=Confidence.HIGH,
        title="Secret left in git history",
        why_it_matters=(
            "Anyone with the repo history can read this secret, even if "
            "the current code no longer has it."
        ),
        how_to_fix=(
            "Remove the secret from git history with git filter-repo, "
            "then rotate it. Deleting the file alone is not enough."
        ),
        cwe="CWE-798",
    ),
    "WEAK_PASSWORD_RULE": RuleMeta(
        severity=Severity.MEDIUM,
        category=FindingCategory.AUTH,
        confidence=Confidence.HIGH,
        title="Weak password rule",
        why_it_matters=(
            "Short passwords fall to automated guessing in minutes, and "
            "your users pay for the break-in."
        ),
        how_to_fix=(
            "Require at least 8 characters with a number, and check the "
            "rule on the server as well as in the form."
        ),
        cwe="CWE-521",
    ),
    "DEBUG_MODE": RuleMeta(
        severity=Severity.LOW,
        category=FindingCategory.CONFIG,
        confidence=Confidence.HIGH,
        title="Debug mode is on",
        why_it_matters=(
            "Debug pages show file paths, settings, and sometimes data to "
            "anyone who triggers an error."
        ),
        how_to_fix=(
            "Turn debug off in production. Keep it on only on your own machine for local work."
        ),
        cwe="CWE-489",
    ),
    "CORS_WILDCARD": RuleMeta(
        severity=Severity.MEDIUM,
        category=FindingCategory.CONFIG,
        confidence=Confidence.HIGH,
        title="CORS allows any origin",
        why_it_matters=(
            "A malicious site can make your users' browsers call your API and act on their behalf."
        ),
        how_to_fix=("List the exact origins you trust instead of allowing every origin."),
        cwe="CWE-942",
    ),
    "SQL_INJECTION": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.INJECTION,
        confidence=Confidence.MEDIUM,
        title="SQL injection risk",
        why_it_matters=(
            "SQL injection can read, change, or delete your whole database through one input field."
        ),
        how_to_fix=(
            "Use a parameterized query with placeholders instead of "
            "building the SQL string from a variable."
        ),
        cwe="CWE-89",
    ),
    "XSS": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.XSS,
        confidence=Confidence.MEDIUM,
        title="Unescaped data in HTML",
        why_it_matters=(
            "Cross-site scripting lets an attacker steal sessions, change "
            "what your users see, and act as them."
        ),
        how_to_fix=(
            "Escape user data before putting it in HTML, or use safe DOM methods like textContent."
        ),
        cwe="CWE-79",
    ),
    "COMMAND_INJECTION": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.INJECTION,
        confidence=Confidence.MEDIUM,
        title="Command injection risk",
        why_it_matters=(
            "Command injection hands an attacker the keys to your server: "
            "read files, steal data, or take the machine over."
        ),
        how_to_fix=(
            "Run the command with a fixed list of arguments and no shell, "
            "and never pass user input straight to it."
        ),
        cwe="CWE-78",
    ),
    "WEAK_CRYPTO": RuleMeta(
        severity=Severity.MEDIUM,
        category=FindingCategory.CONFIG,
        confidence=Confidence.MEDIUM,
        title="Weak cryptography",
        why_it_matters=(
            "Weak crypto is breakable with public tools, so passwords and "
            "tokens protected by it are not really protected."
        ),
        how_to_fix=(
            "Use hashlib.sha256 or a proper password hasher instead, and "
            "use the secrets module for tokens."
        ),
        cwe="CWE-327",
    ),
    "CVE_DEP": RuleMeta(
        severity=Severity.MEDIUM,
        category=FindingCategory.DEPENDENCY,
        confidence=Confidence.HIGH,
        title="Dependency with a known vulnerability",
        why_it_matters=(
            "Known vulnerabilities have public exploits, so attackers "
            "scan for exactly these versions."
        ),
        how_to_fix=(
            "Upgrade the dependency to the fixed version, then run the "
            "check again to confirm it is clean."
        ),
    ),
    "SUPABASE_NO_RLS": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.ACCESS_CONTROL,
        confidence=Confidence.MEDIUM,
        title="Supabase table without Row Level Security",
        why_it_matters=(
            "Without RLS, your database is open to anyone who finds your "
            "public key, which ships in your app."
        ),
        how_to_fix=(
            "Turn on Row Level Security for the table and add a policy "
            "that only lets the right users read and write."
        ),
        cwe="CWE-862",
    ),
    "SUPABASE_SERVICE_KEY_FRONTEND": RuleMeta(
        severity=Severity.CRITICAL,
        category=FindingCategory.SECRETS,
        confidence=Confidence.HIGH,
        title="Supabase service-role key in frontend code",
        why_it_matters=(
            "A service-role key in the browser gives anyone full admin access to your database."
        ),
        how_to_fix=(
            "Keep the service-role key on the server only. Call Supabase "
            "from a server route instead of the browser."
        ),
        cwe="CWE-798",
    ),
    "SECRET_IN_PUBLIC_VAR": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.SECRETS,
        confidence=Confidence.MEDIUM,
        title="Secret in a public variable",
        why_it_matters=(
            "Anything in a public variable is visible to every visitor, "
            "so a secret there is public."
        ),
        how_to_fix=(
            "Move the secret to a server-only environment variable. Never "
            "put secrets in NEXT_PUBLIC_ or VITE_ variables."
        ),
        cwe="CWE-798",
    ),
    "FIREBASE_OPEN_RULES": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.ACCESS_CONTROL,
        confidence=Confidence.HIGH,
        title="Firebase rules allow anyone to read and write",
        why_it_matters=(
            "Open rules mean anyone on the internet can read, change, or delete your users' data."
        ),
        how_to_fix=(
            "Require a signed-in user in the rules, and limit reads and "
            "writes to each user's own data."
        ),
        cwe="CWE-862",
    ),
    "API_ROUTE_NO_AUTH": RuleMeta(
        severity=Severity.MEDIUM,
        category=FindingCategory.ACCESS_CONTROL,
        confidence=Confidence.MEDIUM,
        title="API route has no auth check",
        why_it_matters=(
            "An API route without auth lets anyone call it, even for "
            "actions meant for signed-in users only."
        ),
        how_to_fix=("Add a login, session, or token check at the top of the route handler."),
        cwe="CWE-862",
    ),
    "LLM_KEY_FROM_BROWSER": RuleMeta(
        severity=Severity.HIGH,
        category=FindingCategory.SECRETS,
        confidence=Confidence.MEDIUM,
        title="LLM API key used from the browser",
        why_it_matters=(
            "A leaked LLM key lets strangers run up your bill and read "
            "what your users send to the AI."
        ),
        how_to_fix=("Move the LLM call to a server route and keep the API key on the server."),
        cwe="CWE-798",
    ),
}


def build_fix_guidance(rule_id: str, how_extra: str | None = None) -> str:
    """Markdown fix guidance: "Why it matters" then "How to fix"."""
    meta = RULES.get(rule_id)
    why = meta.why_it_matters if meta else GENERIC_WHY
    how = meta.how_to_fix if meta else GENERIC_FIX
    if how_extra:
        how = f"{how} {how_extra}"
    return f"## Why it matters\n\n{why}\n\n## How to fix\n\n{how}\n"


def make_finding(
    *,
    rule_id: str,
    engine: FindingEngine,
    file: str | None,
    start_line: int | None,
    snippet_text: str | None = None,
    title: str | None = None,
    severity: Severity | None = None,
    confidence: Confidence | None = None,
    category: FindingCategory | None = None,
    trace: list[TraceStep] | None = None,
    evidence: Evidence | None = None,
    how_extra: str | None = None,
) -> Finding:
    """Build a Finding from the rule metadata table.

    Unknown rule ids (e.g. semgrep rules) fall back to generic metadata;
    callers pass explicit severity/title for those.
    """
    meta = RULES.get(rule_id)
    return Finding(
        id=uuid.uuid4(),
        rule_id=rule_id,
        engine=engine,
        category=category or (meta.category if meta else FindingCategory.OTHER),
        severity=severity or (meta.severity if meta else Severity.MEDIUM),
        confidence=confidence or (meta.confidence if meta else Confidence.MEDIUM),
        cwe=meta.cwe if meta else None,
        title=title or (meta.title if meta else rule_id),
        file=file,
        start_line=start_line,
        end_line=start_line,
        snippet=snippet_text,
        trace=trace or [],
        evidence=evidence or Evidence(),
        fix_guidance=build_fix_guidance(rule_id, how_extra),
    )
