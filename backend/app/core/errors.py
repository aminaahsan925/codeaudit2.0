"""Exception handling: every error becomes `{"error": {"code", "message"}}`.

Raise `AppError` (or a subclass) from services for expected failures; its
message is shown to the client, so keep it safe and user-facing. Starlette /
FastAPI `HTTPException`s are mapped to the standard codes with generic
messages. Anything else is logged server-side with its stack trace and
returned as a generic 500.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.security import security_headers
from app.schemas.error import ErrorCode

logger = logging.getLogger(__name__)

STATUS_TO_CODE: Final[Mapping[int, ErrorCode]] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
}

DEFAULT_MESSAGES: Final[Mapping[ErrorCode, str]] = {
    ErrorCode.BAD_REQUEST: "The request is malformed.",
    ErrorCode.UNAUTHORIZED: "Authentication is required.",
    ErrorCode.FORBIDDEN: "You are not allowed to perform this action.",
    ErrorCode.NOT_FOUND: "Resource not found.",
    ErrorCode.METHOD_NOT_ALLOWED: "Method not allowed for this resource.",
    ErrorCode.PAYLOAD_TOO_LARGE: "Request body is too large.",
    ErrorCode.VALIDATION_ERROR: "The request failed validation.",
    ErrorCode.RATE_LIMITED: "Too many audit runs. Try again later.",
    ErrorCode.INTERNAL_ERROR: "An unexpected error occurred.",
}

# Response headers from an HTTPException that are safe to pass through.
_PASSTHROUGH_HEADERS: Final = frozenset({"allow", "www-authenticate", "retry-after"})
_SAFE_LOC_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]{0,63}$")
_MAX_REPORTED_FIELDS: Final = 5


class AppError(Exception):
    """An expected error with a client-safe message."""

    status_code: int = 400
    code: ErrorCode = ErrorCode.BAD_REQUEST

    def __init__(
        self,
        message: str | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.message = message or DEFAULT_MESSAGES[self.code]
        self.headers = dict(headers or {})
        super().__init__(self.message)


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class RateLimitedError(AppError):
    status_code = 429
    code = ErrorCode.RATE_LIMITED


def error_body(code: ErrorCode, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code.value, "message": message}}


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_body(code, message or DEFAULT_MESSAGES[code]),
        headers=dict(headers) if headers else None,
    )


def code_for_status(status_code: int) -> ErrorCode:
    if status_code in STATUS_TO_CODE:
        return STATUS_TO_CODE[status_code]
    return ErrorCode.INTERNAL_ERROR if status_code >= 500 else ErrorCode.BAD_REQUEST


def _validation_message(errors: Sequence[Any]) -> str:
    """Name the failing fields without echoing any submitted values."""
    fields: list[str] = []
    for error in errors:
        loc = error.get("loc", ()) if isinstance(error, Mapping) else ()
        parts = [
            str(part)
            for part in loc
            if isinstance(part, int) or (isinstance(part, str) and _SAFE_LOC_PART.match(part))
        ]
        if parts:
            fields.append(".".join(parts))
    unique = list(dict.fromkeys(fields))
    if not unique:
        return DEFAULT_MESSAGES[ErrorCode.VALIDATION_ERROR]
    shown = ", ".join(unique[:_MAX_REPORTED_FIELDS])
    more = len(unique) - _MAX_REPORTED_FIELDS
    suffix = f" (and {more} more)" if more > 0 else ""
    return f"Invalid or missing value for: {shown}{suffix}."


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.headers)


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = code_for_status(exc.status_code)
    headers = {
        name: value
        for name, value in (exc.headers or {}).items()
        if name.lower() in _PASSTHROUGH_HEADERS
    }
    if code is ErrorCode.UNAUTHORIZED:
        headers.setdefault("WWW-Authenticate", "Bearer")
    status_code = exc.status_code if 400 <= exc.status_code < 600 else 500
    return error_response(status_code, code, headers=headers)


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(isinstance(e, Mapping) and e.get("type") == "json_invalid" for e in errors):
        return error_response(400, ErrorCode.BAD_REQUEST, "Request body is not valid JSON.")
    return error_response(422, ErrorCode.VALIDATION_ERROR, _validation_message(errors))


def build_unhandled_exception_handler(
    *, hsts: bool
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    """Handler for anything unexpected: log the stack, return a generic 500.

    It runs outside the middleware stack (in Starlette's ServerErrorMiddleware),
    so it adds the security headers itself.
    """

    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            exc_info=exc,
            extra={"method": request.method, "path": request.url.path},
        )
        response = error_response(500, ErrorCode.INTERNAL_ERROR)
        for name, value in security_headers(request.url.path, hsts=hsts):
            response.headers[name] = value
        return response

    return unhandled_exception_handler


def register_exception_handlers(app: FastAPI, *, hsts: bool) -> None:
    # Handlers are typed with their concrete exception; Starlette dispatches by class.
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, build_unhandled_exception_handler(hsts=hsts))
