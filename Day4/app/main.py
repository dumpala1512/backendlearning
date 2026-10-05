from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import project_config
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
        "description": "Operations on films catalog with real asynchronous SQLAlchemy 2.0 queries.",
    },
    {
        "name": "Reviews",
        "description": "Operations on film reviews and ratings with real asynchronous SQLAlchemy queries.",
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
    title=f"{project_config.PROJECT_NAME} (Day 4 - PostgreSQL + SQLAlchemy 2.0 Async)",
    version=project_config.API_VERSION,
    description=(
        "A production-style REST API demonstrating real asynchronous PostgreSQL database integration "
        "using SQLAlchemy 2.0 Async (create_async_engine, async_sessionmaker, AsyncSession), "
        "typed ORM models (User, Film, Review), relationships with eager loading, and async DAO queries."
    ),
    lifespan=lifespan,
    openapi_tags=openapi_tags,
)

# Apply CORS middleware configured from static project settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=project_config.ALLOWED_CORS_ORIGINS,   # list of origins that are allowed to make requests
    allow_credentials=True,                      # allow credentials to be sent
    allow_methods=["*"],                       # allow all HTTP methods
    allow_headers=["*"],                       # allow all headers
)

import uuid
from fastapi import Request, Response


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """Automatically attach or generate X-Trace-Id on every HTTP request and response."""
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    response: Response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


# Root-level health endpoint: GET /health
app.include_router(health_router)

# Versioned API routes under /api/v1
app.include_router(api_v1_router, prefix=project_config.API_V1_PREFIX)


# Domain exception handlers
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import DuplicateEntityError, EntityNotFoundError


@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(DuplicateEntityError)
async def duplicate_entity_handler(request: Request, exc: DuplicateEntityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
