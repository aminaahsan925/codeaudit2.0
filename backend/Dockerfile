# syntax=docker/dockerfile:1

# Base images are pinned by multi-arch index digest; the tag is kept for readability.
# To update: docker buildx imagetools inspect <image>:<tag>
FROM ghcr.io/astral-sh/uv:0.11.23@sha256:d0a0a753ab981624b49c97abc98821c1c09f4ca69d1ef5cee69c501be3d88479 AS uv

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY --from=uv /uv /usr/local/bin/uv

# System tools the app needs at runtime:
# - git: cloning GitHub repos for code scans (GitHub URL audits fail without it)
# - curl + ca-certificates: downloading the scanner binaries below
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# External scanners, pinned and verified by checksum. gitleaks matches the
# version pinned in .github/workflows/ci.yml. semgrep is deliberately NOT
# installed: it is too heavy for this image, the native rules cover its
# checks, and the code falls back gracefully when it is missing.
ARG GITLEAKS_VERSION=8.30.1
ARG GITLEAKS_SHA256=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
ARG OSV_SCANNER_VERSION=2.7.1
ARG OSV_SCANNER_SHA256=fb7dab19a8bd9bbe5c3189f09d4b7ee1820c9553a23bac202648a56efd2f6ee8
RUN curl -sSfL -o /tmp/gitleaks.tar.gz \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    && echo "${GITLEAKS_SHA256}  /tmp/gitleaks.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks \
    && rm /tmp/gitleaks.tar.gz \
    && curl -sSfL -o /usr/local/bin/osv-scanner \
        "https://github.com/google/osv-scanner/releases/download/v${OSV_SCANNER_VERSION}/osv-scanner_linux_amd64" \
    && echo "${OSV_SCANNER_SHA256}  /usr/local/bin/osv-scanner" | sha256sum -c - \
    && chmod +x /usr/local/bin/osv-scanner \
    && gitleaks version \
    && osv-scanner --version

WORKDIR /app

# Dependencies first for layer caching; the lockfile must be up to date.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Chromium for the Playwright journey runner. --with-deps installs the
# system libraries the browser needs. Browsers go to PLAYWRIGHT_BROWSERS_PATH
# (a shared path, not /root/.cache) so the non-root app user can run them.
RUN .venv/bin/playwright install --with-deps chromium

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY start.sh ./start.sh

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/artifacts \
    && chown -R 10001:10001 /ms-playwright /app/artifacts \
    && chmod +x /app/start.sh

ENV PATH="/app/.venv/bin:${PATH}"

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, sys, urllib.request; port = os.environ.get('PORT', '8000'); sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + port + '/api/health', timeout=3).status == 200 else 1)"

# Configuration (ENVIRONMENT, DATABASE_URL, ...) is supplied at runtime, never baked in.
# start.sh runs database migrations, then starts uvicorn on $PORT (default 8000).
CMD ["/app/start.sh"]
