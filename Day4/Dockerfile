# ==============================================================================
# Stage 1: Build stage (Installs all dependencies with uv)
# ==============================================================================
FROM python:3.13-slim AS builder

# Copy uv binary directly from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Enable bytecode compilation for faster cold starts
ENV UV_COMPILE_BYTECODE=1

# Copy lockfile and project configuration only to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into /app/.venv (including dev dependencies for pre-deployment tests)
RUN uv sync --frozen --no-editable

# ==============================================================================
# Stage 2: Final Lean Runtime stage (only runtime requirements)
# ==============================================================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Environment settings: point to virtual environment and disable buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root system user for security hardening
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copy the pre-built virtual environment from builder stage
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application source, migrations, scripts, tests, and configuration
COPY --chown=appuser:appgroup app/ ./app
COPY --chown=appuser:appgroup worker/ ./worker
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup alembic.ini ./alembic.ini
COPY --chown=appuser:appgroup scripts/ ./scripts
COPY --chown=appuser:appgroup tests/ ./tests
COPY --chown=appuser:appgroup pytest.ini ./pytest.ini

# Normalize shell script line endings (CRLF -> LF) and make executable
RUN sed -i 's/\r$//' scripts/*.sh && chmod +x scripts/*.sh

# Switch to non-root user
USER appuser

# Expose default FastAPI port
EXPOSE 8000

# Native Python healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

# Container entrypoint runs safety gate via startup.sh before launching server
ENTRYPOINT ["scripts/startup.sh"]

# Default server start command arguments forwarded to uvicorn
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
