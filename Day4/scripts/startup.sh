#!/usr/bin/env sh
# ==============================================================================
# Application Startup Orchestration Script
# Coordinates pre-deployment safety checks and launches the FastAPI server.
#
# Process flow:
#   1. Runs predeploy-check directly to validate env, db, redis, and tests.
#   2. Exits immediately if any pre-deployment check fails.
#   3. Starts FastAPI via Uvicorn only after all safety checks pass.
#   4. Forwards all command-line arguments directly to Uvicorn.
#   5. Replaces shell process with Uvicorn process using exec.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== [Startup] Film Review Platform Application Gateway ==="

# ------------------------------------------------------------------------------
# 1. Execute pre-deployment safety gate via predeploy-check
# ------------------------------------------------------------------------------
echo "=== [Startup] Executing pre-deployment safety gate (Option B: predeploy_gate.py) ==="

if [ -f "${SCRIPT_DIR}/predeploy_gate.py" ]; then
    python "${SCRIPT_DIR}/predeploy_gate.py"
elif command -v predeploy-check >/dev/null 2>&1; then
    predeploy-check
elif [ -f ".venv/bin/predeploy-check" ]; then
    .venv/bin/predeploy-check
elif [ -f ".venv/Scripts/predeploy-check.exe" ]; then
    .venv/Scripts/predeploy-check.exe
else
    python -m predeploy_checker.cli
fi

echo "=== [Startup] All pre-deployment safety checks passed successfully ==="

# ------------------------------------------------------------------------------
# Optional database schema migrations & idempotent seed (if postgres configured)
# ------------------------------------------------------------------------------
DB_URL=$(python -c "from app.core.config import settings; print(settings.DATABASE_URL)" 2>/dev/null || true)
case "$DB_URL" in
    *postgres*)
        if command -v alembic >/dev/null 2>&1 && [ -f "alembic.ini" ]; then
            echo "=== [Startup] Applying database schema migrations ==="
            alembic upgrade head || true
        fi

        if [ -f "${SCRIPT_DIR}/seed.py" ]; then
            echo "=== [Startup] Running idempotent database seed ==="
            python "${SCRIPT_DIR}/seed.py" || true
        fi
        ;;
esac

# ------------------------------------------------------------------------------
# 2. Start FastAPI application with Uvicorn
# ------------------------------------------------------------------------------
echo "=== [Startup] Launching FastAPI application server via Uvicorn ==="

if [ $# -eq 0 ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    # Strip redundant leading "uvicorn" if passed in command arguments
    if [ "$1" = "uvicorn" ]; then
        shift
    fi
    exec uvicorn "$@"
fi
