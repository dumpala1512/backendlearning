from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import project_config
from app.core.lifespan import lifespan
from app.exceptions.handlers import register_exception_handlers
from app.logging.config import configure_logging
from app.middleware.request_id import RequestIDMiddleware
from app.routers.api import api_v1_router
from app.routers.health import router as health_router

# Configure global structured JSON logging before app bootstrap
configure_logging()
logger = logging.getLogger("app.main")

# OpenAPI tags metadata for structured /docs grouping
openapi_tags = [
    {
        "name": "Health",
        "description": "System health and status endpoints with dependency-injected diagnostics.",
    },
    {
        "name": "Films",
        
        "description": "Films catalog managed via Service Layer orchestration, domain rules, and async DAO queries.",
    },
    {
        "name": "Reviews",
        "description": "Film reviews and ratings enforcing domain business rules (Rule 1 & Rule 2) through Service Layer.",
    },
    {
        "name": "Authentication",
        "description": "User registration with bcrypt password hashing, login token issuance (access + refresh tokens), and access token refresh.",
    },
    {
        "name": "Users",
        "description": "User account and profile operations.",
    },
    {
        "name": "Admin",
        "description": "Administrative metrics and platform operations.",
    },
    {
        "name": "Serialization",
        "description": "Pydantic v2 serialization demonstrations.",
    },
]

app = FastAPI(
    title=f"{project_config.PROJECT_NAME} (JWT Authentication & RBAC)",
    version=project_config.API_VERSION,
    description=(
        "Production REST API featuring stateless JWT authentication (access & refresh tokens with bcrypt hashing), "
        "reusable dependency-injected authentication guards, a clean layered architecture (Route -> Service -> DAO -> AsyncSession -> Database), "
        "strict domain business rules (Rule 1: one review per film per user, Rule 2: author-only review updates, "
        "Rule 3: no soft delete of films with active reviews), centralized domain exception handling, "
        "and structured JSON logging with request-scoped tracing."
    ),
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

# Apply CORS middleware configured from static project settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=project_config.ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request-scoped logging & tracing middleware
app.add_middleware(RequestIDMiddleware)

# Root-level health endpoint: GET /health
app.include_router(health_router)

# Versioned API routes under /api/v1
app.include_router(api_v1_router, prefix=project_config.API_V1_PREFIX)

# Centralized domain exception handlers
register_exception_handlers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
