"""SSRF-safe HTTP client for live checks.

Every request target is validated before it is fetched: the hostname is
resolved and every resolved address must be public, unless loopback and
private targets are explicitly allowed (local demos only, never in
production). Redirects are followed manually so each redirect target is
re-validated the same way instead of being followed blindly.

The cloud metadata addresses are always blocked, even when loopback
targets are allowed: reaching them is the whole point of an SSRF attack.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import httpx

if TYPE_CHECKING:
    from app.core.config import Settings

TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 5

# Largest response body the client will read. A malicious target can
# otherwise return a multi-gigabyte body and exhaust server memory;
# callers only ever need the first bytes (evidence is truncated to 500
# chars), so anything past this is dropped, not buffered.
MAX_BODY_BYTES = 5 * 1024 * 1024

# Cloud metadata endpoints. 169.254.169.254 is the AWS/GCP/Azure address;
# 100.100.100.100 is Alibaba Cloud's. Both stay blocked unconditionally.
METADATA_IPS = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),
        ipaddress.ip_address("100.100.100.100"),
    }
)

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class SsrfBlockedError(ValueError):
    """Raised when a live-check target is not a safe public URL."""


class TooManyRedirectsError(RuntimeError):
    """Raised when a request exceeds the redirect limit."""


def loopback_allowed(settings: Settings) -> bool:
    """True only when loopback/private live checks are enabled outside production."""
    return bool(getattr(settings, "allow_loopback_live_checks", False)) and (
        settings.environment != "production"
    )


def resolve_host(hostname: str, port: int) -> list[str]:
    """Resolve a hostname to its addresses (all answers, deduplicated).

    Kept as a module-level function so tests can substitute it without
    touching the network.
    """
    infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    return list(dict.fromkeys(info[4][0] for info in infos))


def _check_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, *, allow_loopback: bool) -> None:
    """Raise SsrfBlockedError unless this address is safe to contact."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        # ::ffff:127.0.0.1 is 127.0.0.1; judge the mapped address.
        ip = ip.ipv4_mapped
    if ip in METADATA_IPS:
        raise SsrfBlockedError(f"address {ip} is a cloud metadata endpoint")
    if ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        raise SsrfBlockedError(f"address {ip} is not a public address")
    if (ip.is_loopback or ip.is_private) and not allow_loopback:
        raise SsrfBlockedError(
            f"address {ip} is loopback or private; "
            "loopback/private targets need allow_loopback_live_checks "
            "outside production"
        )


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def assert_url_allowed(url: str, *, allow_loopback: bool) -> None:
    """Validate a live-check target URL, raising SsrfBlockedError if unsafe.

    The scheme must be http or https, the host must resolve, and every
    resolved address must be public (or loopback/private when explicitly
    allowed). Unresolvable hosts are blocked: an address that cannot be
    checked cannot be trusted.
    """
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise SsrfBlockedError(f"target {url!r} is not a valid URL") from exc
    if parsed.scheme not in ("http", "https"):
        raise SsrfBlockedError(f"target {url!r} must use http or https")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise SsrfBlockedError(f"target {url!r} has no hostname")
    try:
        port = parsed.port or _default_port(parsed.scheme)
    except ValueError as exc:
        raise SsrfBlockedError(f"target {url!r} has an invalid port") from exc
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        _check_ip(literal, allow_loopback=allow_loopback)
        return
    try:
        addresses = resolve_host(host, port)
    except (socket.gaierror, OSError, UnicodeError) as exc:
        raise SsrfBlockedError(f"target {url!r}: could not resolve {host}") from exc
    if not addresses:
        raise SsrfBlockedError(f"target {url!r}: could not resolve {host}")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        _check_ip(ip, allow_loopback=allow_loopback)


class SsrfSafeClient:
    """An httpx client that validates every URL (and every redirect) first.

    Redirects are followed manually, at most MAX_REDIRECTS times, with the
    target re-validated before each hop. Each request times out after
    TIMEOUT_SECONDS. Proxy environment variables are ignored: live checks
    always go direct.
    """

    def __init__(
        self,
        allow_loopback: bool = False,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._allow_loopback = allow_loopback
        self._client = httpx.Client(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> SsrfSafeClient:
        return cls(loopback_allowed(settings), transport=transport)

    def __enter__(self) -> SsrfSafeClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        return self.request("GET", url, headers=headers, follow_redirects=follow_redirects)

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        return self.request(
            "POST", url, headers=headers, data=data, follow_redirects=follow_redirects
        )

    def _fetch(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Fetch one URL, reading at most MAX_BODY_BYTES of the response.

        The returned response keeps the real status code, headers, and
        request, so redirect handling works on it exactly as before; only
        the body is truncated when the target sends more than the cap.
        """
        with self._client.stream(method, url, headers=headers, data=data) as response:
            body = bytearray()
            for chunk in response.iter_bytes(chunk_size=65536):
                remaining = MAX_BODY_BYTES - len(body)
                if remaining <= 0:
                    break
                body += chunk[:remaining]
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                content=bytes(body),
                request=response.request,
            )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        """Send a request, validating the URL and each redirect target."""
        assert_url_allowed(url, allow_loopback=self._allow_loopback)
        response = self._fetch(method, url, headers=headers, data=data)
        redirects = 0
        while (
            follow_redirects
            and response.status_code in _REDIRECT_STATUSES
            and "location" in response.headers
        ):
            if redirects >= MAX_REDIRECTS:
                raise TooManyRedirectsError(f"stopped after {MAX_REDIRECTS} redirects from {url}")
            next_url = urljoin(str(response.url), response.headers["location"])
            assert_url_allowed(next_url, allow_loopback=self._allow_loopback)
            if response.status_code in (301, 302, 303):
                # Browsers turn these into GETs; a POST body must not leak
                # to the redirect target.
                method, data = "GET", None
            response = self._fetch(method, next_url, headers=headers, data=data)
            redirects += 1
        return response
