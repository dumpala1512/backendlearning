# Film Review Platform API (Day 1)

A clean, production-style FastAPI application skeleton built with a 4-layered architecture, managed with `uv`.

---

## 🏗 Project Architecture & Structure

This project follows a strict separation of concerns across four distinct layers:

```
Routes (Routers)  -->  Handlers  -->  Services  -->  DAO (Data Access Object)
```

```
app/
├── main.py              # FastAPI initialization, lifespan & router mounting
├── core/
│   ├── config.py        # Application configuration & settings
│   └── lifespan.py      # Lifespan context manager (startup/shutdown events)
├── models/              # Internal domain models (dataclasses)
│   ├── film.py
│   ├── review.py
│   └── user.py
├── schemas/             # Pydantic validation & response schemas
│   ├── common.py
│   ├── film.py
│   ├── review.py
│   └── user.py
├── dao/                 # Data Access Layer (handles all data operations)
│   ├── film_dao.py
│   ├── review_dao.py
│   └── user_dao.py
├── services/            # Business Logic Layer (business rules & logic only)
│   ├── film_service.py
│   ├── review_service.py
│   └── user_service.py
├── handlers/            # HTTP Orchestration Layer (HTTP status, error handling)
│   ├── film_handler.py
│   ├── review_handler.py
│   ├── auth_handler.py
│   └── user_handler.py
└── routers/             # Routing Layer (endpoints, parameter parsing & validation)
    ├── api.py           # Aggregates routers under /api/v1
    ├── health.py        # GET /health
    ├── films.py         # Film endpoints
    ├── reviews.py       # Review endpoints
    ├── auth.py          # Authentication endpoints
    └── users.py         # User and admin endpoints
```

---

## 🚀 Getting Started

### 1. Run the Development Server
You can run the API server using either command:

```bash
uv run uvicorn app.main:app --reload
```
or via the project CLI script:
```bash
uv run day1
```

The server starts at `http://127.0.0.1:8000`.

### 2. Interactive API Documentation
- **Swagger UI (`/docs`)**: Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (`/redoc`)**: Visit [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3. Run Tests
```bash
uv run pytest
```

---

## 📡 Registered Endpoints

### 🩺 Health
- `GET /health` - System health status & UTC timestamp

### 🎬 Films (`/api/v1/films`)
- `GET /api/v1/films` - List films (demonstrating **Query parameters**: `genre`, `limit`)
- `GET /api/v1/films/{film_id}` - Get film by ID (demonstrating **Path parameter**: `film_id`)
- `POST /api/v1/films` - Create a film (demonstrating **Request body**: `FilmCreate`)
- `PATCH /api/v1/films/{film_id}` - Partially update film (**Path parameter** + **Request body**)
- `DELETE /api/v1/films/{film_id}` - Delete film (**Path parameter**)

### ⭐ Reviews (`/api/v1`)
- `GET /api/v1/films/{film_id}/reviews` - List reviews for a specific film
- `POST /api/v1/films/{film_id}/reviews` - Create review for a film
- `PATCH /api/v1/reviews/{review_id}` - Update a review
- `DELETE /api/v1/reviews/{review_id}` - Delete a review

### 🔐 Authentication (`/api/v1/auth`)
- `POST /api/v1/auth/register` - Register a new user account
- `POST /api/v1/auth/login` - Authenticate and obtain access token

### 👤 Users & Admin (`/api/v1`)
- `GET /api/v1/users/me` - Current user profile
- `GET /api/v1/admin/stats` - Platform metrics and counts

---

## 💡 Reflection & Architecture Questions

### 1. Why FastAPI?
- **High Performance**: Built on Starlette (ASGI) and Pydantic, FastAPI is on par with NodeJS and Go in raw throughput.
- **Automatic OpenAPI Documentation**: Automatically generates interactive `/docs` (Swagger UI) and `/redoc` from Python type hints and schemas.
- **Type Safety and Autocompletion**: Leverages modern Python type annotations, enabling IDE autocomplete, static type checking, and automatic payload parsing.
- **Built-in Validation & Serialization**: Pydantic validates incoming request bodies, query parameters, and path variables automatically, returning clear JSON 422 errors on invalid input.

### 2. Why Layered Architecture?
- **Separation of Concerns**: Each layer has a single, well-defined responsibility:
  - **Routers**: HTTP transport, URL routing, parameter extraction.
  - **Handlers**: Orchestration, translating HTTP concerns and status codes.
  - **Services**: Pure business rules and domain logic.
  - **DAO**: Data storage, querying, and persistence.
- **Testability**: Layers can be isolated and unit-tested without needing a live HTTP server or a real database.
- **Maintainability & Scalability**: Changes to the persistence mechanism (e.g., switching from in-memory/mock storage to PostgreSQL or MongoDB) only impact the DAO layer, leaving the routers and services intact.

### 3. Difference Between Path and Query Parameters?
- **Path Parameters (`/films/{film_id}`)**:
  - Part of the URL path itself.
  - Identifies a **specific resource** or entity.
  - Typically **required** (e.g. `film_id=1`).
- **Query Parameters (`/films?genre=Sci-Fi&limit=10`)**:
  - Appended after the `?` delimiter as key-value pairs.
  - Used for **filtering, sorting, searching, or pagination** of resource collections.
  - Usually **optional** with default values (e.g. `limit=10`).

### 4. Why Response Models?
- **Data Filtering & Security**: Prevents accidental leakage of sensitive internal fields (e.g., `hashed_password` or internal database keys) to the client.
- **Contract Enforcement**: Guarantees the output strictly conforms to the promised API schema.
- **Automatic Serialization**: Automatically converts internal objects (dataclasses, ORM models) into JSON-compatible formats.
- **OpenAPI Schema Accuracy**: Generates precise OpenAPI response schemas for clients and SDK generators.

### 5. Why Lifespan Instead of `@app.on_event`?
- **Standard ASGI Specification**: `@app.on_event("startup")` and `@app.on_event("shutdown")` are deprecated in Starlette/FastAPI.
- **Unified Context Management**: The `lifespan` handler uses Python's `@asynccontextmanager`, allowing clean setup before `yield` and teardown after `yield` within the same scope.
- **Shared State & Error Handling**: Resources (e.g., database connection pools, HTTP clients, background workers) can be safely initialized, passed to the application state, and guaranteed to close gracefully even if startup errors occur.

### 6. How Does `/docs` Get Generated?
- FastAPI inspects all declared routes, path parameters, query parameters, request bodies (Pydantic models), response models, and docstrings.
- It synthesizes this metadata into an **OpenAPI 3.0+ JSON specification** at runtime (served at `/openapi.json`).
- The `/docs` endpoint serves the **Swagger UI** single-page application, which fetches `/openapi.json` and renders the interactive documentation UI.

### 7. Why Keep All Data Access Inside the DAO?
- **Single Source of Truth**: All queries, mutations, transactions, and data interactions reside in one place.
- **Decoupling from Storage Engine**: Upstream business logic in services is completely agnostic to whether data is stored in PostgreSQL, SQLite, Redis, or in-memory dictionaries.
- **Consistent Data Invariants**: Centralizes indexing, caching, and connection management, preventing fragmented or duplicate SQL/ORM queries scattered throughout controllers or route handlers.
