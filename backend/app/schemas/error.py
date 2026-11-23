"""Standard error envelope returned by every non-2xx response."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ErrorCode(StrEnum):
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    """`{"error": {"code": ..., "message": ...}}`"""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


def error_responses(*status_codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI `responses=` entries documenting the error envelope."""
    return {code: {"model": ErrorResponse} for code in status_codes}
