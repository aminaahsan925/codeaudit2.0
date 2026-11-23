"""Structured (JSON lines) logging on top of the standard library.

Every record passes through a redaction step so bearer tokens, Authorization
headers and credentials embedded in URLs never reach the log output.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any, Final

_HANDLER_NAME: Final = "launchaudit"

# Attributes present on every LogRecord; anything else came from `extra=`.
_RESERVED_ATTRS: Final = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
    | {"message", "asctime", "color_message"}  # color_message: uvicorn's ANSI duplicate
)

_SENSITIVE_KEY = re.compile(
    r"(authorization|cookie|password|passwd|secret|token|api[_-]?key|credential)", re.IGNORECASE
)
_REDACTIONS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    # "Authorization: Bearer abc", "authorization=Basic abc"
    (
        re.compile(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)([A-Za-z]+\s+)?[^\s'\",;]+"),
        r"\1[REDACTED]",
    ),
    # Bare "Bearer <token>"
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    # Sensitive query parameters: ?token=..., &api_key=...
    (
        re.compile(
            r"(?i)([?&](?:access_token|token|api[_-]?key|apikey|key|secret|password|signature)=)"
            r"[^&\s\"']+"
        ),
        r"\1[REDACTED]",
    ),
    # scheme://user:password@host
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]+@"), r"\1[REDACTED]@"),
)
REDACTED: Final = "[REDACTED]"


def redact(text: str) -> str:
    """Remove credentials from free text before it is logged."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _safe_extra(key: str, value: Any) -> Any:
    if _SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, int | float | bool) or value is None:
        return value
    return redact(repr(value))


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        for key, value in vars(record).items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = _safe_extra(key, value)
        if record.exc_info:
            payload["exc_info"] = redact(self.formatException(record.exc_info))
        if record.stack_info:
            payload["stack_info"] = redact(self.formatStack(record.stack_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON handler on the root logger. Safe to call repeatedly."""
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        if handler.get_name() == _HANDLER_NAME:
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Route the server's own loggers through the same redacting JSON handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        server_logger = logging.getLogger(name)
        server_logger.handlers.clear()
        server_logger.propagate = True

    # Never log SQL statements with bound values, whatever the app log level.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
