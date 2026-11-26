#!/bin/sh
# Start script for the LaunchAudit backend.
#
# Runs the database migrations first (the deployed database starts empty,
# and the app expects the migrated schema), then starts the API server.
# Used as the Docker image CMD; see docs/deployment.md.

set -eu

cd "$(dirname "$0")"

# Render hands out postgres:// URLs, but the app config only accepts the
# postgresql+psycopg:// or sqlite:// schemes, so rewrite when needed.
# A URL that already uses postgresql+psycopg:// or sqlite:// is untouched.
case "${DATABASE_URL:-}" in
  postgres://*)
    DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}"
    export DATABASE_URL
    ;;
  postgresql://*)
    DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}"
    export DATABASE_URL
    ;;
esac

echo "Running database migrations..."
alembic upgrade head

echo "Starting LaunchAudit API..."
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}" --no-server-header
