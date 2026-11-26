"""In-memory rate limits for audit runs.

One limit for every caller: `settings.audit_rate_limit_per_hour` runs per
hour per key. The key is the bearer token for authenticated callers and the
client IP for guests. Adapted from the old build's `ratelimit.py`.
"""

from __future__ import annotations

import threading
import time

from fastapi import Request

from app.core.config import Settings
from app.core.errors import RateLimitedError

WINDOW_SECONDS = 3600

_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def _prune(key: str, now: float) -> list[float]:
    kept = [t for t in _hits.get(key, []) if now - t < WINDOW_SECONDS]
    _hits[key] = kept
    return kept


def check_and_record(key: str, limit: int) -> bool:
    """Record a run attempt. True when allowed, False when over the limit."""
    now = time.monotonic()
    with _lock:
        kept = _prune(key, now)
        if len(kept) >= limit:
            return False
        kept.append(now)
        return True


def rate_limit_key(request: Request, token: str | None) -> str:
    """Rate-limit key: the bearer token when authenticated, else the client IP."""
    if token:
        return f"token:{token}"
    host = request.client.host if request.client is not None else "unknown"
    return f"ip:{host}"


def enforce_audit_rate_limit(request: Request, settings: Settings, token: str | None) -> None:
    """Raise RateLimitedError when the caller has used up their hourly runs."""
    key = rate_limit_key(request, token)
    if not check_and_record(key, settings.audit_rate_limit_per_hour):
        raise RateLimitedError("Too many audit runs. Try again later.")


def reset() -> None:
    """Clear all recorded hits (tests only)."""
    with _lock:
        _hits.clear()
