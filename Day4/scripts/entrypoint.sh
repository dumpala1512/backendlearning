#!/usr/bin/env sh
set -e

# =============================================================================
# Database Migration & Seed Automation Script for Local Development
# =============================================================================

echo "Starting database migration..."
alembic upgrade head
echo "Database migration completed."

echo "Starting seed data..."
python scripts/seed.py
echo "Seed data completed."

echo "Development database is ready."

if [ $# -gt 0 ]; then
    exec "$@"
fi
