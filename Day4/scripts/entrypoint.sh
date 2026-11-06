#!/usr/bin/env sh
set -e

# ==============================================================================
# Container Entrypoint for FastAPI Application
# Runs database schema migrations and seed scripts before starting the server.
# If either step fails, the container exits with a non-zero exit code.
# ==============================================================================

echo "=== [API Entrypoint] Starting database migrations ==="
if ! alembic upgrade head; then
    echo "[API Entrypoint] FATAL: Database migrations failed! Exiting." >&2
    exit 1
fi
echo "=== [API Entrypoint] Database migrations applied successfully ==="

echo "=== [API Entrypoint] Running idempotent database seed ==="
if ! python scripts/seed.py; then
    echo "[API Entrypoint] FATAL: Data seeding script failed! Exiting." >&2
    exit 1
fi
echo "=== [API Entrypoint] Database seeded successfully ==="

echo "=== [API Entrypoint] Starting FastAPI application server ==="
exec "$@"
