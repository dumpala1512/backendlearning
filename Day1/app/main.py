from fastapi import FastAPI
from app.core.config import settings
from app.core.lifespan import lifespan
from app.routers.api import api_v1_router
from app.routers.health import router as health_router

# OpenAPI tags metadata for structured /docs grouping
openapi_tags = [
    {
        "name": "Health",
        "description": "System health and status endpoints.",
    },
    {
        "name": "Films",
        "description": "Operations on films catalog (browse, search, create, update, delete).",
    },
    {
        "name": "Reviews",
        "description": "Operations on film reviews and ratings.",
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
]

app = FastAPI(
    title=settings.PROJECT_NAME,    
    version=settings.VERSION,
    description="A layered, production-style REST API for the Film Review Platform.",
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

# Root-level health endpoint: GET /health
app.include_router(health_router)

# Versioned API routes under /api/v1
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
