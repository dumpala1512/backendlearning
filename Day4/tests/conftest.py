from __future__ import annotations

from collections.abc import AsyncGenerator
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.security import create_access_token
from app.dependencies import get_db
from app.main import app
# Import all models to ensure they are registered on Base.metadata
from app.models.film import Film
from app.models.review import Review
from app.models.user import User
from app.models.watchlist import Watchlist

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest.fixture
def default_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth_token(default_user_id: uuid.UUID) -> str:
    return create_access_token(
        data={
            "sub": str(default_user_id),
            "username": "test_admin_user",
            "role": "admin",
        }
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_token(default_user_id: uuid.UUID) -> str:
    return create_access_token(
        data={
            "sub": str(default_user_id),
            "username": "sarah_admin",
            "role": "admin",
        }
    )


@pytest.fixture
def critic_token() -> str:
    return create_access_token(
        data={
            "sub": str(uuid.uuid4()),
            "username": "marcus_critic",
            "role": "critic",
        }
    )


@pytest.fixture
def viewer_token() -> str:
    return create_access_token(
        data={
            "sub": str(uuid.uuid4()),
            "username": "alex_viewer",
            "role": "viewer",
        }
    )


import fakeredis.aioredis
from app.core.redis import get_redis_client


@pytest.fixture
async def fake_redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.flushall()
    await fake.aclose()


@pytest.fixture
async def client(test_engine, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(client: AsyncClient, auth_headers: dict[str, str]) -> AsyncClient:
    client.headers.update(auth_headers)
    return client


@pytest.fixture
async def admin_client(client: AsyncClient, test_engine, admin_token: str) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as ac:
        yield ac


@pytest.fixture
async def critic_client(client: AsyncClient, test_engine, critic_token: str) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {critic_token}"},
    ) as ac:
        yield ac


@pytest.fixture
async def viewer_client(client: AsyncClient, test_engine, viewer_token: str) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {viewer_token}"},
    ) as ac:
        yield ac
