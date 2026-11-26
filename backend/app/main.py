"""Application factory: settings, logging, middleware, error handlers, routers.

There is deliberately no module-level app, so importing this module never reads
configuration. Serve it with `uvicorn app.main:create_app --factory`.
"""

import logging

from fastapi import FastAPI

from app.api.routers import auth, health, reports, runs
from app.core.config import Settings, get_settings, validate_startup_config
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.security import (
    CORSMiddlewareWithErrorEnvelope,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

API_PREFIX = "/api"
OPENAPI_URL = f"{API_PREFIX}/openapi.json"
DOCS_URL = f"{API_PREFIX}/docs"
DOCS_OAUTH2_REDIRECT_URL = f"{DOCS_URL}/oauth2-redirect"

CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_HEADERS = ["Authorization", "Content-Type"]

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API. Raises `SettingsError` if the configuration is invalid."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    validate_startup_config(settings)

    production = settings.is_production
    app = FastAPI(
        title="LaunchAudit API",
        version=settings.app_version,
        openapi_url=None if production else OPENAPI_URL,
        docs_url=None if production else DOCS_URL,
        swagger_ui_oauth2_redirect_url=None if production else DOCS_OAUTH2_REDIRECT_URL,
        redoc_url=None,
    )
    app.state.settings = settings

    register_exception_handlers(app, hsts=production)

    # Middleware added last runs first: security headers -> CORS -> size limit -> app.
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        CORSMiddlewareWithErrorEnvelope,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts=production,
        csp_exempt_paths=() if production else (DOCS_URL, DOCS_OAUTH2_REDIRECT_URL),
    )

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(runs.router, prefix=API_PREFIX)
    app.include_router(reports.router, prefix=API_PREFIX)

    logger.info(
        "Application configured",
        extra={"environment": settings.environment, "version": settings.app_version},
    )
    return app
