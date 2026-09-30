# Film Review Platform — Day 3: Configuration & Shared Dependencies (FastAPI Dependency Injection)

Welcome to Day 3 of the Film Review Platform backend engineering series. This phase establishes a **centralized, fail-fast configuration system** and an **extensible dependency injection layer** using FastAPI.

---

## 📌 Architecture Overview

```
                                  +-------------------+
                                  |     .env file     |
                                  +---------+---------+
                                            |
                                            v
                             +-----------------------------+
                             |   app/core/config.py        |
                             |   - Typed Settings class    |
                             |   - Fail-fast validation    |
                             |   - Singleton 'settings'    |
                             +--------------+--------------+
                                            |
                         +------------------+------------------+
                         |                                     |
                         v                                     v
             +-----------------------+             +-----------------------+
             | get_settings() dep    |             | FastAPI app (main.py) |
             +-----------+-----------+             | - CORS Middleware     |
                         |                         | - OpenAPI metadata    |
                         |                         +-----------------------+
                         |
      +------------------+------------------+
      |                                     |
      v                                     v
+-------------------------+   +---------------------------+   +-------------------------+
| get_db() dep            |   | get_trace_id() dep        |   | Routes (films, reviews) |
| - Composed on settings  |   | - Inspects X-Trace-Id     |   | - Obtains resources     |
| - Generator (yield)     |   | - Auto-generates UUID4    |   |   exclusively via       |
| - Deterministic cleanup |   | - OpenAPI documented      |   |   Depends(...)          |
+-------------------------+   +---------------------------+   +-------------------------+
```

---

## 🎯 Deliverables Implemented

### 1. Centralized Configuration Module (`app/core/config.py`)
- **Exclusive environment access**: The **only** module in the entire application authorized to read environment variables. All other modules are forbidden from calling `os.getenv()` or `os.environ`.
- **Loaded from `.env`**: Uses Pydantic v2 `pydantic-settings` to load configuration directly from `.env` with fallback paths.
- **Strongly Typed**:
  - `DATABASE_URL: str`
  - `TOKEN_SECRET_KEY: str` (enforces minimum 16-character length)
  - `ACCESS_TOKEN_EXPIRE_MINUTES: int` (with `ACCESS_TOKEN_EXPIRY_DURATION` property alias)
  - `REFRESH_TOKEN_EXPIRE_DAYS: int` (with `REFRESH_TOKEN_EXPIRY_DURATION` property alias)
  - `ALLOWED_CORS_ORIGINS: list[str]` (robust validator parsing JSON arrays or comma-separated strings)
  - `API_VERSION: str` (with `VERSION` property alias)
  - Metadata: `PROJECT_NAME`, `API_V1_PREFIX`, `ENVIRONMENT`, `DEBUG`

### 2. Fail-Fast Configuration Validation
- If any required configuration variable is missing (such as `DATABASE_URL` or `TOKEN_SECRET_KEY`), application initialization fails immediately with a descriptive diagnostic message in `stderr`, raising a `RuntimeError` before the server can start accepting requests.

### 3. Singleton Configuration Object
- `settings = _initialize_settings()` is instantiated exactly once at module load time and shared across the application.

### 4. Configuration Dependency (`get_settings`)
- Reusable FastAPI dependency located in [`app/dependencies.py`](app/dependencies.py).
- Route handlers inject `settings: Settings = Depends(get_settings)`. Handlers **never** import the raw `settings` singleton directly.

### 5. Placeholder Database Session Dependency (`get_db`)
- Generator dependency (`yield`) mimicking SQLAlchemy/ORM async session lifecycles.
- Structured with `try ... yield session ... finally: session.close()` to guarantee deterministic connection cleanup after each request.
- Composable: depends on `get_settings` to retrieve `DATABASE_URL`.
- Future-proof: on Day 4, replacing this placeholder with real async SQLAlchemy sessions will require **zero changes to route signatures**.

### 6. Request Trace ID Dependency (`get_trace_id`)
- Inspects the `X-Trace-Id` incoming HTTP header using FastAPI's `Header` parameter.
- If the header is supplied by the client, it is validated and used.
- If omitted or empty, generates a cryptographically random UUID4.
- Automatically registered in the generated OpenAPI documentation under `parameters` (`in: header`).

### 7. Dependency Injection in Route Handlers
Applied across multiple routes in [`app/routers/films.py`](app/routers/films.py), [`app/routers/reviews.py`](app/routers/reviews.py), and [`app/routers/health.py`](app/routers/health.py):
- `GET /api/v1/films`
- `GET /api/v1/films/{film_id}`
- `POST /api/v1/films`
- `GET /api/v1/films/{film_id}/reviews`
- `POST /api/v1/films/{film_id}/reviews`
- `GET /health`

Each route handler receives `(settings: Settings = Depends(get_settings), db: DatabaseSession = Depends(get_db), trace_id: str = Depends(get_trace_id))`, logs structured request traces, and echoes the trace ID back in the `X-Trace-Id` HTTP response header.

### 8. Environment Files (`.env` and `.env.example`)
- `.env` populated with all required configuration values.
- `.env.example` provided as a reference template for production deployments.

### 9. OpenAPI Documentation Verification
- `X-Trace-Id` header parameter is automatically reflected in OpenAPI schema (`/docs` and `/openapi.json`) for all dependent routes without manual schema decorators.

---

## 📂 Project Structure

```
Day3/
├── .env                     # Local environment configuration
├── .env.example             # Template environment configuration
├── .dockerignore
├── .gitignore
├── .python-version
├── Dockerfile               # Multi-stage production container build
├── README.md                # Day 3 documentation
├── docker-compose.yml       # Container orchestration with .env binding
├── pyproject.toml           # Project dependencies & tool configurations
├── pyrightconfig.json
├── uv.lock                  # Pinned dependency lockfile
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app initialization & CORS setup
│   ├── dependencies.py      # get_settings, get_db, get_trace_id dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Centralized Settings & fail-fast validator
│   │   └── lifespan.py      # App startup/shutdown lifespan context
│   ├── dao/                 # Data access layer (in-memory DAOs)
│   ├── handlers/            # Business logic handlers
│   ├── models/              # Pydantic v2 schemas
│   ├── routers/
│   │   ├── api.py           # V1 route aggregator
│   │   ├── films.py         # Film routes with dependency injection
│   │   ├── reviews.py       # Review routes with dependency injection
│   │   ├── health.py        # Health route with dependency injection
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── serialization.py
│   └── services/            # Domain services
└── tests/
    ├── test_config.py       # Unit tests for settings, typing & fail-fast
    ├── test_dependencies.py # Tests for dependency injection lifecycle
    └── test_openapi.py      # Tests for OpenAPI schema reflection
```

---

## 🚀 Getting Started

### 1. Setup Environment
```bash
# Navigate to Day3 directory
cd Day3

# Install dependencies using uv
uv sync --dev
```

### 2. Run Test Suite
```bash
uv run pytest -v
```

Expected output:
```
tests/test_config.py::test_singleton_settings_loaded_from_env PASSED
tests/test_config.py::test_settings_property_aliases PASSED
tests/test_config.py::test_cors_origins_parsing PASSED
tests/test_config.py::test_fail_fast_missing_required_fields PASSED
tests/test_config.py::test_fail_fast_short_token_secret_key PASSED
tests/test_config.py::test_no_getenv_outside_config_module PASSED
tests/test_dependencies.py::test_get_settings_dependency PASSED
tests/test_dependencies.py::test_database_session_lifecycle PASSED
tests/test_dependencies.py::test_trace_id_custom_client_header PASSED
tests/test_dependencies.py::test_trace_id_generated_when_header_absent PASSED
tests/test_dependencies.py::test_films_route_dependency_injection PASSED
tests/test_dependencies.py::test_reviews_route_dependency_injection PASSED
tests/test_dependencies.py::test_health_check_dependency_injection PASSED
tests/test_dependencies.py::test_dependency_override_isolation PASSED
tests/test_openapi.py::test_openapi_schema_contains_injected_trace_header PASSED
tests/test_openapi.py::test_openapi_metadata PASSED
======================== 16 passed in 2.14s ========================
```

### 3. Run the Development Server
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up --build -d

# View application logs
docker compose logs -f api

# Stop container
docker compose down
```
