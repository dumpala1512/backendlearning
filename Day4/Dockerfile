# ==========================================
# Stage 1: Builder (Installs dependencies with uv)
# ==========================================
FROM python:3.13-slim AS builder

# Copy uv binary directly from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Compile Python bytecode for fast cold starts
ENV UV_COMPILE_BYTECODE=1

# Copy lockfile and project configuration
COPY pyproject.toml uv.lock ./

# Install production dependencies only into /app/.venv
RUN uv sync --frozen --no-dev --no-editable

# ==========================================
# Stage 2: Final Lean Runtime
# ==========================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Environment settings: point to venv and disable buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root system user for security hardening
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copy the pre-built virtualenv with correct ownership (avoids duplicate layer bloat)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application source code and migrations with correct ownership
COPY --chown=appuser:appgroup app/ ./app
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup scripts/ ./scripts

# Switch to non-root user
USER appuser

# Expose default FastAPI port
EXPOSE 8000

# Native healthcheck using Python standard library (no curl or extra apt packages needed)
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Start the application using uvicorn from the virtual environment
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
