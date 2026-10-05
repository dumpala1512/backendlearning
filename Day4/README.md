# Film Review Platform — Day 4: PostgreSQL + SQLAlchemy 2.0 Async Setup

Welcome to Day 4 of the Film Review Platform backend engineering series. This phase replaces the placeholder database session with a real asynchronous PostgreSQL database using **SQLAlchemy 2.0 Async** (`asyncpg`), typed ORM models, eager joined loading, and asynchronous DAO queries while maintaining the existing architectural structure.

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
                             |   - settings.DATABASE_URL   |
                             +--------------+--------------+
                                            |
                                            v
                             +-----------------------------+
                             |   app/core/database.py      |
                             |   - create_async_engine()   |
                             |   - async_sessionmaker()    |
                             |   - Base (DeclarativeBase)  |
                             |   - init_db() utility       |
                             +--------------+--------------+
                                            |
                         +------------------+------------------+
                         |                                     |
                         v                                     v
             +-----------------------+             +-----------------------+
             | app/models/orm.py     |             | app/dependencies.py   |
             | - User (ORM)          |             | - get_db() ->         |
             | - Film (ORM)          |             |   AsyncGenerator[     |
             | - Review (ORM)        |             |     AsyncSession]     |
             | - Relationships & FKs |             | - Auto close & rollbk |
             | - server_default      |             +-----------+-----------+
             +-----------+-----------+                         |
                         |                                     |
                         +------------------+------------------+
                                            |
                                            v
                               +-------------------------+
                               | app/dao/film_dao.py     |
                               | - async get_all(db,...) |
                               | - async get_by_id(db,.) |
                               | - async create(db,...)  |
                               +------------+------------+
                                            |
                                            v
                               +-------------------------+
                               | app/routers/films.py    |
                               | - async def list_films  |
                               | - await film_dao.get_all|
                               | - FilmResponse (Day 2)  |
                               +-------------------------+
```

---

## 🎯 Deliverables Implemented

### 1. Database Configuration (`app/core/database.py`)
- **Connection String Source**: Read exclusively from `settings.DATABASE_URL` via `app.core.config.settings`.
- **Async Engine**: Configured using `create_async_engine()` with the `asyncpg` driver.
- **Connection Pooling**:
  - `pool_size=10`
  - `max_overflow=20`
  - `pool_pre_ping=True` (verifies connections before checkout)
  - `pool_recycle=1800` (recycles connections older than 30 minutes)
  - `echo=settings.DEBUG`
- **Async Sessionmaker**: Created with `expire_on_commit=False` and `class_=AsyncSession`.
- **Reusable Module**: Exposes `engine`, `async_session_factory`, and declarative `Base`.

### 2. Database Session Dependency (`app/dependencies.py`)
- Replaces the placeholder session dependency with real `AsyncSession`.
- **Per-request Session**: Creates a request-scoped `AsyncSession`.
- **Deterministic Cleanup**: Uses an async context manager generator (`async with async_session_factory() as session: yield session`), automatically closing connections after each HTTP request and rolling back on exceptions.
- **Preserved Route Signatures**: Backward compatibility alias `DatabaseSession = AsyncSession` guarantees existing route signatures and types continue working seamlessly.

### 3. SQLAlchemy 2.0 Typed ORM Models (`app/models/orm.py`)
Fully typed models using modern SQLAlchemy 2.0 `Mapped`, `mapped_column`, and `relationship`:

#### `User` (`users` table)
- `id: Mapped[int]` (Primary Key, autoincrement)
- `username: Mapped[str]` (String(50), unique, index, not nullable)
- `email: Mapped[str]` (String(255), unique, index, not nullable)
- `role: Mapped[str]` (String(20), default "user", not nullable)
- `hashed_password: Mapped[str]` (String(255), not nullable)
- `created_at: Mapped[datetime]` (`server_default=func.now()`, database-side default, not generated by Python code)
- `reviews: Mapped[list[Review]]` (One-to-many relationship)

#### `Film` (`films` table)
- `id: Mapped[int]` (Primary Key, autoincrement)
- `title: Mapped[str]` (String(200), index, not nullable)
- `director: Mapped[str]` (String(100), not nullable)
- `release_year: Mapped[int]` (Integer, index, not nullable)
- `genre: Mapped[str]` (String(50), index, not nullable)
- `description: Mapped[str]` (Text, default "", not nullable)
- `created_at: Mapped[datetime]` (`server_default=func.now()`, database-side default, not generated by Python code)
- `reviews: Mapped[list[Review]]` (One-to-many relationship)

#### `Review` (`reviews` table)
- `id: Mapped[int]` (Primary Key, autoincrement)
- `film_id: Mapped[int]` (ForeignKey `films.id`, ondelete `CASCADE`, index, not nullable)
- `user_id: Mapped[int | None]` (ForeignKey `users.id`, ondelete `SET NULL`, index, nullable)
- `rating: Mapped[int]` (Integer, not nullable)
- `review: Mapped[str]` (Text, not nullable)
- `reviewer_display_name: Mapped[str]` (String(50), default "Anonymous Critic", not nullable)
- `created_at: Mapped[datetime]` (`server_default=func.now()`, database-side default, not generated by Python code)
- `film: Mapped[Film]` (Many-to-one relationship)
- `user: Mapped[User | None]` (Many-to-one relationship)

### 4. Relationships & Single-Query Joined Loading
- Configured bidirectional relationships between `User`, `Film`, and `Review`.
- Supports loading a review together with its film title and reviewer username in a single SQL query via `joinedload`:
  ```python
  stmt = select(ReviewORM).options(
      joinedload(ReviewORM.film),
      joinedload(ReviewORM.user),
  )
  ```

### 5. DAO & Route Updates (`app/dao/film_dao.py`, `app/routers/films.py`)
- **Async DAO**: `film_dao.get_all(db: AsyncSession, ...)` executes real asynchronous SQLAlchemy `select()` queries.
- **Route Handler**: `GET /api/v1/films` awaits the DAO call and returns existing Day 2 response schemas (`FilmResponse` with computed `years_since_release`) without altering the JSON response format.

### 6. Database Utility (`app/core/database.py`)
- Standalone utility function `init_db()` using `Base.metadata.create_all`.
- Runnable directly via `python -m app.core.database` if needed.
- **Not called automatically on application startup**.
- **Production Note included in code**:
  > `Base.metadata.create_all()` creates missing tables only. It does not manage schema evolution. Production applications should use Alembic migrations instead.

---

## 🚀 Running the Project

### Option A: Local Development with uv

1. Install dependencies:
   ```bash
   uv sync
   ```

2. (Optional) Initialize tables in your PostgreSQL database:
   ```bash
   uv run python -m app.core.database
   ```

3. Run the test suite:
   ```bash
   uv run pytest -v
   ```

4. Start the API server:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

### Option B: Docker Compose (PostgreSQL + API)

```bash
docker compose up --build
```
This boots:
- `film-review-db-day4`: PostgreSQL 16 on port 5432 with health check.
- `film-review-platform-day4`: FastAPI backend on port 8000 connected to the PostgreSQL container.

---

## 🔄 Database Migrations with Alembic (Async)

In production environments, database schema changes must be version-controlled, auditable, reproducible, and reversible. `Base.metadata.create_all()` is strictly for ephemeral tests and prototypes; all production schema evolution is managed through Alembic.

### 1. Alembic Architecture & Configuration
- **Async Engine**: Configured in `alembic/env.py` using `async_engine_from_config(..., poolclass=pool.NullPool)` and `run_async_migrations()`.
- **Dynamic Configuration**: Automatically loads database credentials directly from `app.core.config.settings.DATABASE_URL`.
- **Target Metadata**: Registered via `from app.core.database import Base` and `import app.schemas`, exposing models to Alembic's autogeneration comparison engine.

### 2. Migration History
The repository includes two version-controlled migrations under `alembic/versions`:

1. **Initial Schema Migration** (`6ec96ce24e17_create_initial_schema.py`):
   - Automatically generated via:
     ```bash
     uv run alembic revision --autogenerate -m "create initial schema"
     ```
   - Creates `users`, `films`, and `reviews` tables along with primary keys, indexes, unique constraints, and foreign key cascades.
   
2. **Watchlist Extension Migration** (`4d1668473519_add_watchlist_table.py`):
   - Extends the schema with a `watchlist` table representing a many-to-many relationship between `users` and `films`.
   - Generated as an independent revision without modifying the first migration:
     ```bash
     uv run alembic revision --autogenerate -m "add watchlist table"
     ```
   - Defines composite primary key `(user_id, film_id)`, cascading foreign keys, and `created_at` timestamp.

### 3. Alembic CLI Commands Reference

| Command | Purpose |
| :--- | :--- |
| `uv run alembic current` | Shows the currently applied revision in the database. |
| `uv run alembic history` | Lists all migrations in chronological order. |
| `uv run alembic upgrade head` | Migrates the database forward to the most recent revision. |
| `uv run alembic downgrade -1` | Rolls back the single most recent migration. |
| `uv run alembic revision --autogenerate -m "..."` | Compares current ORM models against DB schema and generates migration. |

---

## 🌱 Idempotent Data Seeding (`scripts/seed.py`)

Seed data is an independent, application-level concern and is strictly decoupled from schema migrations.

### Running the Seed Script
```bash
uv run python scripts/seed.py
```

### Key Guarantees:
- **Idempotency**: Running `scripts/seed.py` once or ten times produces the exact same final database state with zero duplicates.
- **Pre-flight Existence Checks**: Verifies existing records using primary/unique keys (`username` for users, `(title, release_year)` for films, `(film_id, user_id)` for reviews).
- **Rich Baseline Dataset**:
  - **12 Films** spanning 7 genres (*Sci-Fi, Action, Thriller, Animation, Comedy, Drama, Crime*).
  - **4 Users** covering distinct roles (*admin, critic, member, user*).
  - **7 Reviews** with realistic ratings and detailed criticism.
  - **6 Watchlist entries** connecting users to films.

---

## 🛠️ Complete Developer Setup Sequence

```bash
# 1. Start the PostgreSQL database
docker compose up -d db

# 2. Run all schema migrations
uv run alembic upgrade head

# 3. Populate baseline seed data
uv run python scripts/seed.py

# 4. Launch the API server
uv run uvicorn app.main:app --reload --port 8000
```
