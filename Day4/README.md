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

### 6. Database Initialization Utility (`app/core/init_db.py`)
- Standalone utility function `init_db(engine)` using `Base.metadata.create_all`.
- Runnable via `python -m app.core.init_db`.
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
   uv run python -m app.core.init_db
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
