"""Rule-based review of findings: verdict, reason, corrected snippet.

Used whenever no AI provider is configured, the providers fail, or a
finding has no code snippet for the model to quote. Templates are adapted
from the old build's ai_review.py and suggestions.py; rule ids match the
ones the scanners emit (see CONTRACT.md v2 and PORTING-NOTES.md).

Rule-based review confirms what the scanner found: it has no new evidence
to overturn a finding, so every template verdict is "confirmed". The
"likely false positive" verdict is for the model path, which actually
reads the code. A template has a corrected snippet only where the fix is
genuinely code; fixes that are process steps (rotate a key, block a path
in the web server) live in the reason instead, and the scanner's own fix
guidance already covers the how-to.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.finding import (
    AIVerdict,
    AIVerdictLabel,
    Finding,
    FindingEngine,
)

MAX_SNIPPET = 500
JOURNEY_RULE_ID = "JOURNEY_STEP_FAILED"


@dataclass(frozen=True)
class RuleTemplate:
    """What rule-based review says about one rule id."""

    verdict: AIVerdictLabel
    reason: str
    fixed_snippet: str | None = None


RULE_REVIEWS: dict[str, RuleTemplate] = {
    "SECRET_GENERIC": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A secret is written directly in the code. Anyone who can read the code can use it."
        ),
        fixed_snippet="SECRET_KEY = os.environ.get('SECRET_KEY')",
    ),
    "SECRET_KNOWN_PREFIX": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("This key format matches a real provider key. Treat it as exposed and rotate it."),
        fixed_snippet="STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')",
    ),
    "HARDCODED_CREDENTIAL": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("A password is written directly in the code. Move it out and change it."),
        fixed_snippet="password = os.environ.get('APP_PASSWORD')",
    ),
    "SECRET_GIT_HISTORY": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A secret is still in the git history. Deleting the file does "
            "not remove it from history. Remove it with git filter-repo, "
            "then rotate it."
        ),
    ),
    "WEAK_PASSWORD_RULE": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("Passwords shorter than 8 characters are allowed. Require at least 8 characters."),
        fixed_snippet=("if len(password) < 8:\n    raise ValueError('Password too short')"),
    ),
    "DEBUG_MODE": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason="Debug mode is on. It can leak internal details in production.",
        fixed_snippet="DEBUG = False",
    ),
    "CORS_WILDCARD": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("Any website can call this API from a browser. List only the origins you trust."),
        fixed_snippet='allow_origins=["https://your-app.example"]',
    ),
    "CORS_OPEN": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "The live app answers cross-origin requests from any origin. "
            "List only the origins you trust."
        ),
        fixed_snippet='allow_origins=["https://your-app.example"]',
    ),
    "SQL_INJECTION": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A database query is built from a variable, so an attacker can "
            "change the query. Use a parameter instead."
        ),
        fixed_snippet='cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))',
    ),
    "XSS": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "User data goes into the page without escaping, so an attacker "
            "can run their own script in your users' browsers. Escape it "
            "or use safe DOM methods."
        ),
        fixed_snippet="element.textContent = userInput",
    ),
    "COMMAND_INJECTION": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A shell command is built from a variable. Run commands with a "
            "fixed list of arguments and no shell."
        ),
        fixed_snippet='subprocess.run(["ls", path], shell=False)',
    ),
    "WEAK_CRYPTO": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "An outdated hash, cipher, or random generator is used where "
            "security matters. Use a modern one."
        ),
        fixed_snippet="hashlib.sha256(data).hexdigest()",
    ),
    "CVE_DEP": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A dependency has a known vulnerability with a public exploit. "
            "Upgrade to the fixed version."
        ),
    ),
    "SUPABASE_NO_RLS": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A Supabase table has no Row Level Security, so anyone with "
            "the public key can read and write it. Turn RLS on and add a "
            "policy."
        ),
        fixed_snippet="alter table my_table enable row level security;",
    ),
    "SUPABASE_SERVICE_KEY_FRONTEND": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "The service-role key bypasses every security rule and is in "
            "code that ships to the browser. Keep it on the server only."
        ),
    ),
    "SECRET_IN_PUBLIC_VAR": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A public variable ships to the browser, so a secret in one is "
            "public. Keep secrets in server-only variables."
        ),
    ),
    "FIREBASE_OPEN_RULES": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("The Firebase rules allow anyone to read and write. Require a signed-in user."),
        fixed_snippet="allow read, write: if request.auth != null;",
    ),
    "API_ROUTE_NO_AUTH": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("This API route runs with no login check. Add one before it does any work."),
        fixed_snippet=(
            "const session = await getSession(req)\nif (!session) return res.status(401).end()"
        ),
    ),
    "LLM_KEY_FROM_BROWSER": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "An LLM API key is used in frontend code, so it ships to every "
            "visitor. Call the LLM from your server."
        ),
    ),
    "EXPOSED_ENV": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "Your environment file is publicly reachable. Block it in the "
            "web server config, and rotate every secret it held."
        ),
    ),
    "EXPOSED_GIT": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("Your git files are publicly reachable. Block them in the web server config."),
    ),
    "SECRETS_IN_JS_BUNDLE": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A JavaScript file served by the app contains a secret. Move "
            "the secret to the server and rotate it."
        ),
    ),
    "MISSING_SECURITY_HEADERS": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "The app is missing security headers that stop common browser "
            "attacks. Add them in one middleware."
        ),
        fixed_snippet="response.headers['X-Content-Type-Options'] = 'nosniff'",
    ),
    "INSECURE_COOKIE": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A cookie is missing HttpOnly or SameSite, so scripts or other "
            "sites can misuse it. Set both flags."
        ),
        fixed_snippet='response.set_cookie("session", value, httponly=True, samesite="lax")',
    ),
    "OPEN_ADMIN_ROUTE": RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=("An admin or debug route is open to anyone. Put it behind a login check."),
    ),
    JOURNEY_RULE_ID: RuleTemplate(
        verdict=AIVerdictLabel.CONFIRMED,
        reason=(
            "A real user flow stops at this step. Check the endpoint and "
            "its error logs for this step, then run the journey again to "
            "confirm the fix."
        ),
    ),
}

DEFAULT_REVIEW = RuleTemplate(
    verdict=AIVerdictLabel.CONFIRMED,
    reason=(
        "This finding needs a fix before launch. Fix the problem, then "
        "run the check again to confirm it is gone."
    ),
)


def rule_based_review(finding: Finding) -> tuple[AIVerdict, str | None]:
    """Review one finding from the template table.

    Returns the verdict and the corrected snippet (None where the fix is
    a process step, not code). The quoted code is the finding's own
    snippet, or empty when the finding has no code to quote.
    """
    if finding.engine == FindingEngine.JOURNEY:
        template = RULE_REVIEWS[JOURNEY_RULE_ID]
    else:
        template = RULE_REVIEWS.get(finding.rule_id, DEFAULT_REVIEW)
    return (
        AIVerdict(
            verdict=template.verdict,
            reason=template.reason,
            quoted_code=(finding.snippet or "")[:MAX_SNIPPET],
        ),
        template.fixed_snippet,
    )
