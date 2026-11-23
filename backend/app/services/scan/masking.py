"""Secret masking and secret-pattern helpers for the code scanner.

Secrets are ALWAYS masked (first 4 chars + "****") in snippets, logs,
errors, reports, API responses, and anything sent to AI. Nothing in this
module ever returns an unmasked secret value.
"""

import re

MAX_SNIPPET = 500

SECRET_NAME_KEYWORDS = (
    "API_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "PRIVATE_KEY",
    "CLIENT_SECRET",
    "ACCESS_KEY",
    "AUTH_TOKEN",
)

PLACEHOLDER_MARKERS = (
    "your-",
    "xxx",
    "changeme",
    "change-me",
    "example",
    "placeholder",
    "todo",
)
PLACEHOLDER_EXACT = {"test", "password"}

ENV_READ_MARKERS = ("os.environ", "os.getenv", "process.env")

# Known key formats (CONTRACT.md rule 2). If one fires on a line, the
# generic secret rule is suppressed for that line.
KNOWN_PREFIX_RES = [
    re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{10,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----"),
]

# Quoted assignment: name = "value" (also "name": "value" dict style).
ASSIGNMENT_RE = re.compile(r"""["']?([A-Za-z_][A-Za-z0-9_.]*)["']?\s*(?:=|:)\s*["']([^"']+)["']""")

# Unquoted assignment (e.g. .env and YAML lines): NAME=value with no quotes.
UNQUOTED_ASSIGN_RE = re.compile(r"""([A-Za-z_][A-Za-z0-9_.]*)\s*[:=]\s*([A-Za-z0-9_./+=-]{8,})""")

# Connection strings: postgres://user:password@host/db. The userinfo
# (credentials) is masked whatever the variable name; the host stays
# visible because it is the useful part of the evidence.
CONNECTION_USERINFO_RE = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)([^/@\s]+@)")

# Bare high-entropy tokens with no assignment context (JWT segments, long
# hex/base64 keys). 40 chars is past any English word or normal identifier;
# "/" is excluded so file paths and URLs are not mangled.
LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-+=]{40,}")


def mask_secret(value: str) -> str:
    """Show at most the first 4 chars of a secret, then ****."""
    if not value:
        return "****"
    return value[:4] + "****"


def is_placeholder(value: str) -> bool:
    """True when a value is a placeholder, not a real secret."""
    lowered = value.strip().lower()
    if lowered in PLACEHOLDER_EXACT:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def is_env_read(line: str) -> bool:
    """True when the line reads a value from the environment."""
    return any(marker in line for marker in ENV_READ_MARKERS)


def is_secret_name(name: str) -> bool:
    """True when a variable name looks like it holds a secret."""
    upper = name.upper()
    return any(keyword in upper for keyword in SECRET_NAME_KEYWORDS)


def has_known_prefix(text: str) -> bool:
    """True when the text contains a known secret key format."""
    return any(pattern.search(text) for pattern in KNOWN_PREFIX_RES)


def mask_text(text: str) -> str:
    """Mask every secret-looking value in a snippet of text."""
    if not text:
        return text
    masked = text
    for pattern in KNOWN_PREFIX_RES:
        masked = pattern.sub(lambda m: mask_secret(m.group(0)), masked)
    masked = CONNECTION_USERINFO_RE.sub(r"\1****@", masked)
    masked = LONG_TOKEN_RE.sub(lambda m: mask_secret(m.group(0)), masked)

    def _mask_assignment(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        if is_secret_name(name) and len(value) >= 8:
            return match.group(0).replace(value, mask_secret(value), 1)
        return match.group(0)

    masked = ASSIGNMENT_RE.sub(_mask_assignment, masked)

    def _mask_unquoted(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        if not is_secret_name(name):
            return match.group(0)
        if value.startswith(("os.environ", "os.getenv", "process.env")):
            return match.group(0)
        return match.group(0).replace(value, mask_secret(value), 1)

    masked = UNQUOTED_ASSIGN_RE.sub(_mask_unquoted, masked)
    return masked


def snippet(line: str) -> str:
    """Masked, trimmed snippet of one source line (max ~500 chars)."""
    return mask_text(line.strip())[:MAX_SNIPPET]
