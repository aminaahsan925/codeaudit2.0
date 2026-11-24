"""Domain ownership verification for live checks.

The server issues the token: the owner requests one for a domain, serves
it at /.well-known/launchaudit-verification.txt, and asks the server to
check it. The token is stored server-side, so a run can only probe a
domain whose owner placed the server-issued token there. A
client-supplied token proves nothing and is never accepted.

The well-known file is the only verification path. A meta tag is weaker:
on some sites user content can inject markup into the home page, so a
tag is not proof of control over the domain.

Verification fetches go through the same SSRF-safe client as the checks,
so a verification attempt can never be used to probe internal addresses.
"""

from __future__ import annotations

import hmac
import ipaddress
import re
from typing import TYPE_CHECKING

import httpx

from .ssrf_client import SsrfBlockedError, SsrfSafeClient, loopback_allowed

if TYPE_CHECKING:
    from app.core.config import Settings

VERIFICATION_PATH = "/.well-known/launchaudit-verification.txt"

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class DomainNotVerifiedError(RuntimeError):
    """Raised when live checks are asked to run on an unverified domain."""


def normalize_domain(value: str) -> str | None:
    """Normalize a domain (host) to lowercase without a trailing dot.

    Returns None when the value is not a bare domain: no scheme, path,
    port, userinfo or whitespace, labels of letters, digits and hyphens
    only, at most 253 characters. Used for token lookup and storage so
    the same domain always maps to the same stored token.
    """
    host = value.strip().lower().rstrip(".")
    if not host or len(host) > 253:
        return None
    if any(char in host for char in ("/", ":", "@", " ", "\t", "\n", "\r")):
        return None
    if not all(_LABEL_RE.match(label) for label in host.split(".")):
        return None
    return host


def is_local_domain(domain: str) -> bool:
    """True for localhost names and loopback/private IP literals.

    Local targets never need a token: the runner treats them as verified
    when loopback checks are enabled outside production.
    """
    host = domain.strip().lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local")):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def verification_url_for(domain: str) -> str:
    """The exact HTTPS URL a domain owner must serve the token at."""
    return f"https://{domain}{VERIFICATION_PATH}"


def _tokens_equal(candidate: str, token: str) -> bool:
    try:
        return hmac.compare_digest(candidate, token)
    except TypeError:
        return False


def _token_file_matches(client: SsrfSafeClient, url: str, token: str) -> bool:
    try:
        response = client.get(url)
    except (httpx.HTTPError, SsrfBlockedError):
        return False
    if response.status_code != 200:
        return False
    return any(_tokens_equal(line.strip(), token) for line in response.text.splitlines())


def verify_domain(url: str, token: str, settings: Settings | None = None) -> bool:
    """True when the domain at `url` serves `token` at the well-known path.

    Only the well-known file counts; a meta tag never verifies. Never
    raises for network or SSRF problems: anything that cannot be verified
    is simply unverified.

    Pass `settings` when loopback/private targets should be reachable
    (local demos with allow_loopback_live_checks); without settings they
    stay blocked.
    """
    if not url or not token:
        return False
    base_url = url.rstrip("/")
    allow_loopback = loopback_allowed(settings) if settings is not None else False
    with SsrfSafeClient(allow_loopback) as client:
        return _token_file_matches(client, base_url + VERIFICATION_PATH, token)


def verify_host_token(domain: str, token: str, settings: Settings | None = None) -> bool:
    """True when `domain` serves `token` at its exact well-known HTTPS URL.

    The fetch goes to https://<domain>/.well-known/launchaudit-verification.txt
    and nowhere else: a token served at any other path, or on the home
    page, does not verify. Never raises for network or SSRF problems.
    """
    normalized = normalize_domain(domain)
    if normalized is None or not token:
        return False
    return verify_domain(f"https://{normalized}", token, settings)
