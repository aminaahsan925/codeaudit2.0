"""Checks against the deployed app (headers, exposed endpoints) via the SSRF-safe client."""

from .checks import CheckOutcome, LiveAppUnreachableError, run_all_checks
from .runner import LiveCheckResult, run_live_checks, run_live_checks_detailed
from .ssrf_client import (
    SsrfBlockedError,
    SsrfSafeClient,
    TooManyRedirectsError,
    loopback_allowed,
)
from .verify import DomainNotVerifiedError, verify_domain

__all__ = [
    "CheckOutcome",
    "DomainNotVerifiedError",
    "LiveAppUnreachableError",
    "LiveCheckResult",
    "SsrfBlockedError",
    "SsrfSafeClient",
    "TooManyRedirectsError",
    "loopback_allowed",
    "run_all_checks",
    "run_live_checks",
    "run_live_checks_detailed",
    "verify_domain",
]
