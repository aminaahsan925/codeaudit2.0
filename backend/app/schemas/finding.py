"""Finding: one problem found by any engine, with the evidence that proves it.

Mirrors `docs/api-contract.md` (Domain schemas -> Finding).
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Optional/defaulted fields are still listed as `required` in the serialization
# schema, so generated client types are `T | null` instead of `T | undefined`.
_RESPONSE_CONFIG = ConfigDict(json_schema_serialization_defaults_required=True)


class FindingEngine(StrEnum):
    NATIVE = "native"
    SEMGREP = "semgrep"
    GITLEAKS = "gitleaks"
    OSV = "osv"
    VIBE = "vibe"
    LIVE = "live"
    JOURNEY = "journey"
    AI = "ai"


class FindingCategory(StrEnum):
    SECRETS = "secrets"
    INJECTION = "injection"
    AUTH = "auth"
    ACCESS_CONTROL = "access_control"
    CONFIG = "config"
    DEPENDENCY = "dependency"
    SSRF = "ssrf"
    XSS = "xss"
    DATA_EXPOSURE = "data_exposure"
    OTHER = "other"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AIVerdictLabel(StrEnum):
    CONFIRMED = "confirmed"
    LIKELY_FALSE_POSITIVE = "likely_false_positive"
    NEEDS_REVIEW = "needs_review"


class FindingStatus(StrEnum):
    OPEN = "open"
    FIXED = "fixed"
    IGNORED = "ignored"
    FALSE_POSITIVE = "false_positive"


class TraceStep(BaseModel):
    """One step of a data-flow trace from source to sink."""

    model_config = _RESPONSE_CONFIG

    file: str
    line: int = Field(ge=1)
    snippet: str
    label: str


class HttpEvidence(BaseModel):
    model_config = _RESPONSE_CONFIG

    method: str
    url: str
    status: int = Field(ge=100, le=599)
    request_headers: dict[str, str] = Field(default_factory=dict)
    response_headers: dict[str, str] = Field(default_factory=dict)
    body_excerpt: str | None = None


class PackageEvidence(BaseModel):
    model_config = _RESPONSE_CONFIG

    name: str
    version: str
    advisory: str


class Evidence(BaseModel):
    """Engine-specific proof. Every key is optional (and may be omitted)."""

    http: HttpEvidence | None = None
    screenshot_url: str | None = None
    secret_preview: str | None = None
    package: PackageEvidence | None = None
    notes: str | None = None


class AIVerdict(BaseModel):
    model_config = _RESPONSE_CONFIG

    verdict: AIVerdictLabel
    reason: str
    quoted_code: str


class Finding(BaseModel):
    model_config = _RESPONSE_CONFIG

    id: UUID
    rule_id: str = Field(min_length=1)
    engine: FindingEngine
    category: FindingCategory
    severity: Severity
    confidence: Confidence
    cwe: str | None = Field(default=None, pattern=r"^CWE-\d+$")
    title: str = Field(min_length=1)
    file: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    snippet: str | None = None
    trace: list[TraceStep] = Field(default_factory=list)
    evidence: Evidence = Field(default_factory=Evidence)
    ai_verdict: AIVerdict | None = None
    fix_guidance: str | None = None
    status: FindingStatus = FindingStatus.OPEN

    @model_validator(mode="after")
    def _check_line_range(self) -> "Finding":
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("end_line must be greater than or equal to start_line")
        return self
