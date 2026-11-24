"""Live app security checks, run against the deployed app over HTTP.

Adapted from the old build's livecheck.py (CONTRACT.md v2, live-checks
section) to this repo's Finding schema. Every finding stores proof in
evidence.http, with the response redacted (secrets masked, max 500 chars).
A check that cannot reach the app is recorded as skipped, never as a
finding; the home page failing to load skips the whole run.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

from app.core.security import mask_secret
from app.schemas.finding import (
    Confidence,
    Evidence,
    Finding,
    FindingCategory,
    FindingEngine,
    HttpEvidence,
    Severity,
)

from .crawl import check_broken_links_and_forms
from .ssrf_client import SsrfBlockedError, SsrfSafeClient

MAX_PROOF = 500
MAX_BUNDLES = 3

SECURITY_HEADERS = (
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
    "Strict-Transport-Security",
)

ADMIN_PATHS = ("/admin", "/debug", "/debug/pprof", "/__debug__")

EVIL_ORIGIN = "https://evil.example"

ENV_LINE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,60}=", re.MULTILINE)
SCRIPT_SRC_RE = re.compile(r"""<script[^>]+src=["']([^"']+\.js[^"']*)["']""", re.IGNORECASE)
SECRET_ASSIGN_RE = re.compile(
    r"""(?:API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|CLIENT_SECRET|ACCESS_KEY)"""
    r"""\s*[:=]\s*["']([^"']{12,})["']"""
)

# Secret shapes that are recognisable on sight (same set as the code scan).
KNOWN_PREFIX_RES = (
    re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{10,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----"),
)

SECRET_NAME_KEYWORDS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "CLIENT_SECRET",
)
QUOTED_ASSIGN_RE = re.compile(r"""([A-Za-z_][A-Za-z0-9_.]*)\s*[:=]\s*["']([^"']{8,})["']""")
UNQUOTED_ASSIGN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*([A-Za-z0-9_./+=-]{8,})")

# Connection strings: postgres://user:password@host/db. The userinfo
# (credentials) is masked whatever the variable name; the host stays
# visible because it is the useful part of the evidence.
CONNECTION_USERINFO_RE = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)([^/@\s]+@)")

# Bare high-entropy tokens with no assignment context (JWT segments, long
# hex/base64 keys). 40 chars is past any English word or normal identifier;
# "/" is excluded so file paths and URLs are not mangled.
LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-+=]{40,}")


class LiveAppUnreachableError(RuntimeError):
    """Raised when the home page cannot be fetched at all."""


class _CheckSkippedError(RuntimeError):
    """Raised by a check that could not run; run_all_checks records it."""


@dataclass
class CheckOutcome:
    """What one live-check run produced.

    `skipped` holds the rule ids of checks that could not run (the app did
    not answer that request); they are never reported as findings.
    """

    findings: list[Finding] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _is_secret_name(name: str) -> bool:
    upper = name.upper()
    return any(keyword in upper for keyword in SECRET_NAME_KEYWORDS)


def mask_text(text: str) -> str:
    """Mask every secret-looking value in a snippet of text."""
    if not text:
        return text
    masked = text
    for pattern in KNOWN_PREFIX_RES:
        masked = pattern.sub(lambda match: mask_secret(match.group(0)), masked)
    masked = CONNECTION_USERINFO_RE.sub(r"\1****@", masked)
    masked = LONG_TOKEN_RE.sub(lambda match: mask_secret(match.group(0)), masked)

    def _mask_quoted(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        if _is_secret_name(name):
            return match.group(0).replace(value, mask_secret(value), 1)
        return match.group(0)

    masked = QUOTED_ASSIGN_RE.sub(_mask_quoted, masked)

    def _mask_unquoted(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        if not _is_secret_name(name):
            return match.group(0)
        if value.startswith(("os.environ", "os.getenv", "process.env")):
            return match.group(0)
        return match.group(0).replace(value, mask_secret(value), 1)

    return UNQUOTED_ASSIGN_RE.sub(_mask_unquoted, masked)


def redact_body(text: str | None) -> str | None:
    """Redact a response body for evidence: secrets masked, max 500 chars."""
    if text is None:
        return None
    return mask_text(text)[:MAX_PROOF]


def _redact_response_headers(headers: httpx.Headers) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() == "set-cookie":
            # Keep the cookie name and flags, mask the value itself.
            first, _, rest = value.partition(";")
            cookie_name, _, cookie_value = first.partition("=")
            masked = f"{cookie_name}={mask_secret(cookie_value.strip())}"
            redacted[name] = f"{masked};{rest}" if rest else masked
        else:
            redacted[name] = mask_text(value)
    return redacted


def _http_evidence(response: httpx.Response) -> HttpEvidence:
    return HttpEvidence(
        method=response.request.method,
        url=str(response.request.url),
        status=response.status_code,
        request_headers=dict(response.request.headers),
        response_headers=_redact_response_headers(response.headers),
        body_excerpt=redact_body(response.text),
    )


def _fix_guidance(why_it_matters: str, how_to_fix: str) -> str:
    return f"## Why it matters\n\n{why_it_matters}\n\n## How to fix\n\n{how_to_fix}"


def _finding(
    *,
    rule_id: str,
    severity: Severity,
    category: FindingCategory,
    title: str,
    why_it_matters: str,
    how_to_fix: str,
    path: str,
    response: httpx.Response,
    cwe: str | None = None,
    snippet: str | None = None,
) -> Finding:
    return Finding(
        id=uuid.uuid4(),
        rule_id=rule_id,
        engine=FindingEngine.LIVE,
        category=category,
        severity=severity,
        confidence=Confidence.HIGH,
        cwe=cwe,
        title=title,
        snippet=snippet,
        evidence=Evidence(
            http=_http_evidence(response),
            notes=f"Path: {path}",
        ),
        fix_guidance=_fix_guidance(why_it_matters, how_to_fix),
    )


def check_exposed_env(client: SsrfSafeClient, base_url: str) -> Finding | None:
    """EXPOSED_ENV [Critical]: GET /.env returns 200 with env content."""
    response = client.get(base_url + "/.env")
    if response.status_code != 200 or not ENV_LINE_RE.search(response.text):
        return None
    return _finding(
        rule_id="EXPOSED_ENV",
        severity=Severity.CRITICAL,
        category=FindingCategory.DATA_EXPOSURE,
        title="Environment file is publicly reachable",
        why_it_matters=(
            "A public .env hands your keys and passwords to anyone who asks "
            "for them. Attackers scan for /.env on every new site."
        ),
        how_to_fix=(
            "Stop serving .env from the web server (deny the path, or keep "
            "the file outside the web root), then rotate every secret that "
            "was in it: the file was public, so treat all of them as leaked."
        ),
        path="/.env",
        response=response,
        cwe="CWE-200",
        snippet=redact_body(response.text),
    )


def check_exposed_git(client: SsrfSafeClient, base_url: str) -> Finding | None:
    """EXPOSED_GIT [High]: GET /.git/HEAD returns 200 with ref content."""
    response = client.get(base_url + "/.git/HEAD")
    if response.status_code != 200 or "ref:" not in response.text:
        return None
    return _finding(
        rule_id="EXPOSED_GIT",
        severity=Severity.HIGH,
        category=FindingCategory.DATA_EXPOSURE,
        title="Git files are publicly reachable",
        why_it_matters=(
            "Exposed git files let anyone download your history, including "
            "secrets you deleted long ago."
        ),
        how_to_fix=(
            "Stop serving .git from the web server (deny the path, or deploy "
            "from a clean checkout without the .git directory), then check "
            "the history for secrets and rotate any that were ever committed."
        ),
        path="/.git/HEAD",
        response=response,
        cwe="CWE-200",
        snippet=redact_body(response.text),
    )


def _find_secret_in_bundle(text: str) -> str | None:
    for pattern in KNOWN_PREFIX_RES:
        match = pattern.search(text)
        if match:
            return match.group(0)
    match = SECRET_ASSIGN_RE.search(text)
    return match.group(1) if match else None


def check_js_bundle_secrets(
    client: SsrfSafeClient, base_url: str, home_text: str
) -> Finding | None:
    """SECRETS_IN_JS_BUNDLE [Critical]: a same-origin JS bundle holds a secret."""
    base_netloc = urlparse(base_url).netloc
    bundle_urls: list[str] = []
    for match in SCRIPT_SRC_RE.finditer(home_text or ""):
        absolute = urljoin(base_url + "/", match.group(1))
        if urlparse(absolute).netloc == base_netloc:
            bundle_urls.append(absolute)
        if len(bundle_urls) >= MAX_BUNDLES:
            break
    for bundle_url in bundle_urls:
        try:
            bundle = client.get(bundle_url)
        except (httpx.HTTPError, SsrfBlockedError):
            continue
        if bundle.status_code != 200:
            continue
        secret = _find_secret_in_bundle(bundle.text)
        if not secret:
            continue
        path = urlparse(bundle_url).path
        return _finding(
            rule_id="SECRETS_IN_JS_BUNDLE",
            severity=Severity.CRITICAL,
            category=FindingCategory.SECRETS,
            title="Secret inside a JavaScript bundle",
            why_it_matters=(
                "Secrets in a bundle are public: every visitor's browser "
                "downloads them, and anyone can use the key as if they "
                "were you."
            ),
            how_to_fix=(
                "Remove the secret from the bundle and rotate it. Move the "
                "call that needs it to your own backend and have the browser "
                "call that instead; never ship a key the browser does not need."
            ),
            path=path,
            response=bundle,
            cwe="CWE-798",
            snippet=redact_body(bundle.text),
        )
    return None


def check_security_headers(home: httpx.Response) -> Finding | None:
    """MISSING_SECURITY_HEADERS [Medium]: 2 or more of the 5 headers absent."""
    present = {name.lower() for name in home.headers}
    missing = [header for header in SECURITY_HEADERS if header.lower() not in present]
    if len(missing) < 2:
        return None
    return _finding(
        rule_id="MISSING_SECURITY_HEADERS",
        severity=Severity.MEDIUM,
        category=FindingCategory.CONFIG,
        title="Security headers are missing",
        why_it_matters=(
            "Security headers stop clickjacking, MIME sniffing, and other "
            "browser attacks for free. Without them the browser has no "
            "instructions to protect your users."
        ),
        how_to_fix=(
            "Send these headers on every response: "
            + ", ".join(missing)
            + ". Most frameworks add them with one middleware or a few "
            "web-server lines."
        ),
        path="/",
        response=home,
        cwe="CWE-693",
    )


def check_cors(client: SsrfSafeClient, base_url: str) -> Finding | None:
    """CORS_OPEN [Medium]: the app answers any origin (or echoes an evil one)."""
    response = client.get(base_url + "/", headers={"Origin": EVIL_ORIGIN})
    allow_origin = response.headers.get("access-control-allow-origin", "")
    if allow_origin not in ("*", EVIL_ORIGIN):
        return None
    return _finding(
        rule_id="CORS_OPEN",
        severity=Severity.MEDIUM,
        category=FindingCategory.ACCESS_CONTROL,
        title="CORS allows any origin",
        why_it_matters=(
            "A malicious site can make your users' browsers call your API and act on their behalf."
        ),
        how_to_fix=(
            "Allow only the origins your own front end uses "
            "(Access-Control-Allow-Origin with an explicit list), and never "
            "use * together with credentials."
        ),
        path="/",
        response=response,
        cwe="CWE-942",
    )


def _parse_cookie(header: str) -> tuple[str, bool, bool, bool] | None:
    """Return (name, has_secure, has_httponly, has_samesite) for Set-Cookie."""
    parts = [part.strip() for part in header.split(";")]
    if not parts or "=" not in parts[0]:
        return None
    name = parts[0].split("=", 1)[0].strip()
    attrs = " ".join(parts[1:]).lower()
    return name, "secure" in attrs, "httponly" in attrs, "samesite" in attrs


def missing_cookie_flags(
    *, secure: bool, httponly: bool, samesite: bool, is_https: bool
) -> list[str]:
    """Which protection flags a cookie lacks.

    Secure is only required over https: over plain http it would stop the
    cookie working at all, so it is not counted there.
    """
    missing: list[str] = []
    if not httponly:
        missing.append("HttpOnly")
    if not samesite:
        missing.append("SameSite")
    if is_https and not secure:
        missing.append("Secure")
    return missing


def _collect_cookies(response: httpx.Response) -> list[tuple[str, bool, bool, bool]]:
    cookies = []
    for header in response.headers.get_list("set-cookie", []):
        parsed = _parse_cookie(header)
        if parsed:
            cookies.append(parsed)
    return cookies


def _login_cookies(
    client: SsrfSafeClient, base_url: str, email: str, password: str
) -> tuple[list[tuple[str, bool, bool, bool]], httpx.Response | None]:
    """POST /login with the test account and return its cookies.

    If login yields no session cookie, the account may not exist yet: sign
    up first with the same credentials and retry once.
    """

    def _try_login() -> tuple[list[tuple[str, bool, bool, bool]], httpx.Response | None]:
        try:
            response = client.post(
                base_url + "/login",
                data={"email": email, "password": password},
                follow_redirects=False,
            )
        except (httpx.HTTPError, SsrfBlockedError):
            return [], None
        return _collect_cookies(response), response

    cookies, response = _try_login()
    if cookies:
        return cookies, response
    try:
        client.post(
            base_url + "/signup",
            data={"name": "Test User", "email": email, "password": password},
            follow_redirects=False,
        )
    except (httpx.HTTPError, SsrfBlockedError):
        return [], None
    return _try_login()


def check_insecure_cookies(
    client: SsrfSafeClient,
    base_url: str,
    home: httpx.Response,
    email: str | None = None,
    password: str | None = None,
) -> Finding | None:
    """INSECURE_COOKIE [Medium]: a cookie missing HttpOnly or SameSite.

    One finding per run, naming the first insecure cookie. Secure is only
    required over https.
    """
    is_https = urlparse(base_url).scheme == "https"
    insecure: list[str] = []
    evidence_response: httpx.Response | None = None
    evidence_path = "/"
    missing_bits: list[str] = []

    def _inspect(
        cookies: list[tuple[str, bool, bool, bool]],
        response: httpx.Response,
        path: str,
    ) -> None:
        nonlocal evidence_response, evidence_path, missing_bits
        for name, secure, httponly, samesite in cookies:
            missing = missing_cookie_flags(
                secure=secure, httponly=httponly, samesite=samesite, is_https=is_https
            )
            if not missing:
                continue
            if name not in insecure:
                insecure.append(name)
            if evidence_response is None:
                evidence_response, evidence_path, missing_bits = response, path, missing

    _inspect(_collect_cookies(home), home, "/")
    if email and password:
        login_cookies, login_response = _login_cookies(client, base_url, email, password)
        if login_response is not None:
            _inspect(login_cookies, login_response, "/login")
    if not insecure or evidence_response is None:
        return None
    return _finding(
        rule_id="INSECURE_COOKIE",
        severity=Severity.MEDIUM,
        category=FindingCategory.CONFIG,
        title="Insecure cookie",
        why_it_matters=(
            "A cookie without HttpOnly can be read by injected scripts, "
            "and one without SameSite can be sent by other sites, which "
            "leads to stolen sessions."
        ),
        how_to_fix=(
            "Set every session cookie with HttpOnly and SameSite=Lax (or "
            "Strict), and add Secure once the app runs over https."
        ),
        path=evidence_path,
        response=evidence_response,
        cwe="CWE-1004",
    )


def check_admin_routes(client: SsrfSafeClient, base_url: str) -> list[Finding]:
    """OPEN_ADMIN_ROUTE [Medium]: an admin/debug route returns a page.

    One finding per open path. A redirect (to login) or a 404 is not a
    finding. If every path fails to answer, the check is skipped.
    """
    findings: list[Finding] = []
    answered = 0
    for admin_path in ADMIN_PATHS:
        try:
            response = client.get(base_url + admin_path, follow_redirects=False)
        except (httpx.HTTPError, SsrfBlockedError):
            continue
        answered += 1
        if response.status_code != 200:
            continue
        findings.append(
            _finding(
                rule_id="OPEN_ADMIN_ROUTE",
                severity=Severity.MEDIUM,
                category=FindingCategory.ACCESS_CONTROL,
                title=f"Open admin route: {admin_path}",
                why_it_matters=(
                    "An open admin or debug route is a door into your app "
                    "that anyone can walk through."
                ),
                how_to_fix=(
                    "Put this route behind login, restrict it to your own "
                    "network, or remove it from the deployed app entirely."
                ),
                path=admin_path,
                response=response,
                cwe="CWE-862",
            )
        )
    if answered == 0:
        raise _CheckSkippedError("admin routes did not answer")
    return findings


def run_all_checks(
    client: SsrfSafeClient,
    base_url: str,
    email: str | None = None,
    password: str | None = None,
) -> CheckOutcome:
    """Run the eight live checks. Raises LiveAppUnreachableError when the
    home page cannot be fetched; individual check failures are recorded as
    skipped in the returned outcome.
    """
    base_url = base_url.rstrip("/")
    try:
        home = client.get(base_url + "/")
    except httpx.HTTPError as exc:
        raise LiveAppUnreachableError(f"could not reach the app at {base_url} ({exc})") from exc

    outcome = CheckOutcome()

    def _run(rule_id: str, func, *args) -> None:
        try:
            result = func(*args)
        except (httpx.HTTPError, SsrfBlockedError, _CheckSkippedError):
            outcome.skipped.append(rule_id)
            return
        if result is None:
            return
        if isinstance(result, list):
            outcome.findings.extend(result)
        else:
            outcome.findings.append(result)

    _run("EXPOSED_ENV", check_exposed_env, client, base_url)
    _run("EXPOSED_GIT", check_exposed_git, client, base_url)
    _run("SECRETS_IN_JS_BUNDLE", check_js_bundle_secrets, client, base_url, home.text or "")
    headers_finding = check_security_headers(home)
    if headers_finding is not None:
        outcome.findings.append(headers_finding)
    _run("CORS_OPEN", check_cors, client, base_url)
    _run("INSECURE_COOKIE", check_insecure_cookies, client, base_url, home, email, password)
    _run("OPEN_ADMIN_ROUTE", check_admin_routes, client, base_url)
    _run("BROKEN_LINKS_AND_FORMS", check_broken_links_and_forms, client, base_url, home)
    return outcome
