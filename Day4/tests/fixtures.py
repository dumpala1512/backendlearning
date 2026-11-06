from __future__ import annotations

from typing import AsyncGenerator
import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
from fastapi import FastAPI

from app.core.redis import get_redis_client
from app.dependencies import get_db
from app.main import app as fastapi_app
from tests.database import create_test_engine, drop_test_db, init_test_db


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Creates the isolated test engine.
    Initializes the database schema only once for the test session.
    Never connects to the production database.
    """
    engine = create_test_engine()
    await init_test_db(engine)

    yield engine

    await drop_test_db(engine)
    await engine.dispose()


@pytest.fixture
async def db_connection(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncConnection, None]:
    """
    Opens one database connection per test.
    """
    async with async_engine.connect() as connection:
        yield connection


@pytest.fixture
async def db_session(
    db_connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an AsyncSession with an isolated transaction for each test.
    Uses nested transaction / SAVEPOINT strategy so that application-level
    commits only release and restart savepoints.
    Automatically rolls back the root transaction after every test,
    ensuring each test starts with a completely clean database state without
    dropping or recreating tables.
    """
    root_trans = await db_connection.begin()
    savepoint = await db_connection.begin_nested()

    session = AsyncSession(
        bind=db_connection,
        expire_on_commit=False,
        autoflush=False,
    )

    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(sess, transaction):
        nonlocal savepoint
        sync_conn = db_connection.sync_connection
        if not savepoint.is_active and sync_conn is not None:
            savepoint = sync_conn.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        if root_trans.is_active:
            await root_trans.rollback()


@pytest.fixture
async def fake_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Provides an isolated in-memory Redis client for caching and token storage."""
    redis_instance = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield redis_instance
    finally:
        await redis_instance.aclose()


@pytest.fixture
def app() -> FastAPI:
    """Returns the FastAPI application instance."""
    return fastapi_app


@pytest.fixture
async def client(
    app: FastAPI,
    db_session: AsyncSession,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Creates an AsyncClient executing directly against the application
    via ASGITransport without starting a live uvicorn server.
    Applies dependency overrides so that every request uses the isolated
    test database and test redis client.
    Cleans up dependency overrides after each test.
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
