from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.lifespan import lifespan
from app.routers.api import api_v1_router
from app.routers.health import router as health_router

# OpenAPI tags metadata for structured /docs grouping
openapi_tags = [
    {
        "name": "Health",
        "description": "System health and status endpoints with dependency-injected diagnostics.",
    },
    {
        "name": "Films",
        "description": "Operations on films catalog with dependency-injected Settings, DatabaseSession, and TraceID.",
    },
    {
        "name": "Reviews",
        "description": "Operations on film reviews and ratings with dependency injection.",
    },
    {
        "name": "Authentication",
        "description": "User registration and authentication tokens.",
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
    title=f"{settings.PROJECT_NAME} (Day 3 - Configuration & Dependencies)",
    version=settings.API_VERSION,
    description=(
        "A production-style REST API demonstrating centralized typed configuration loaded from .env, "
        "fail-fast configuration validation, and reusable FastAPI dependency injection "
        "(get_settings, get_db, get_trace_id)."
    ),
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

# Apply CORS middleware configured from centralized settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint: GET /health
app.include_router(health_router)

# Versioned API routes under /api/v1
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
