"""Domain ownership verification for live checks.

The owner proves they control a domain in one of two ways: serving the
verification token at /.well-known/launchaudit-verification.txt, or adding
a `<meta name="launchaudit-verification" content="<token>">` tag to the
home page. Live checks run only after verification passes.

Verification fetches go through the same SSRF-safe client as the checks,
so a verification attempt can never be used to probe internal addresses.
"""

from __future__ import annotations

import hmac
import re
from typing import TYPE_CHECKING

import httpx

from .ssrf_client import SsrfBlockedError, SsrfSafeClient, loopback_allowed

if TYPE_CHECKING:
    from app.core.config import Settings

VERIFICATION_PATH = "/.well-known/launchaudit-verification.txt"
META_NAME = "launchaudit-verification"

_META_TAG_RE = re.compile(r"<meta[^>]+>", re.IGNORECASE)
_META_ATTR_RE = re.compile(r"""([\w-]+)\s*=\s*["']([^"']*)["']""")


class DomainNotVerifiedError(RuntimeError):
    """Raised when live checks are asked to run on an unverified domain."""


def _tokens_equal(candidate: str, token: str) -> bool:
    try:
        return hmac.compare_digest(candidate, token)
    except TypeError:
        return False


def _token_file_matches(client: SsrfSafeClient, base_url: str, token: str) -> bool:
    try:
        response = client.get(base_url + VERIFICATION_PATH)
    except (httpx.HTTPError, SsrfBlockedError):
        return False
    if response.status_code != 200:
        return False
    return any(_tokens_equal(line.strip(), token) for line in response.text.splitlines())


def _meta_tag_matches(client: SsrfSafeClient, base_url: str, token: str) -> bool:
    try:
        response = client.get(base_url + "/")
    except (httpx.HTTPError, SsrfBlockedError):
        return False
    if response.status_code != 200:
        return False
    for tag in _META_TAG_RE.findall(response.text or ""):
        attrs = {name.lower(): value for name, value in _META_ATTR_RE.findall(tag)}
        content = attrs.get("name") == META_NAME and attrs.get("content")
        if content and _tokens_equal(content.strip(), token):
            return True
    return False


def verify_domain(url: str, token: str, settings: Settings | None = None) -> bool:
    """True when the domain at `url` serves `token` as a verification file
    or a home-page meta tag. Never raises for network or SSRF problems:
    anything that cannot be verified is simply unverified.

    Pass `settings` when loopback/private targets should be reachable
    (local demos with allow_loopback_live_checks); without settings they
    stay blocked.
    """
    if not url or not token:
        return False
    base_url = url.rstrip("/")
    allow_loopback = loopback_allowed(settings) if settings is not None else False
    with SsrfSafeClient(allow_loopback) as client:
        if _token_file_matches(client, base_url, token):
            return True
        return _meta_tag_matches(client, base_url, token)
