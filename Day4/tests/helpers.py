from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User


def create_test_token(
    user_id: uuid.UUID | None = None,
    username: str = "testuser",
    role: str = "viewer",
) -> str:
    """
    Directly create a signed JWT access token for testing with given claims.
    """
    sub_id = user_id or uuid.uuid4()
    payload = {
        "sub": str(sub_id),
        "username": username,
        "role": role,
    }
    return create_access_token(payload)


def get_auth_headers(token: str) -> dict[str, str]:
    """Return standard HTTP Authorization header with Bearer token."""
    return {"Authorization": f"Bearer {token}"}


async def register_user(
    client: httpx.AsyncClient,
    username: str = "test_user",
    email: str = "test_user@example.com",
    password: str = "SecurePass123!",
    role: str = "viewer",
    full_name: str = "Test User",
) -> httpx.Response:
    """Issue a real HTTP POST request to the registration endpoint."""
    payload = {
        "username": username,
        "email": email,
        "password": password,
        "confirm_password": password,
        "role": role,
        "full_name": full_name,
    }
    return await client.post("/api/v1/register", json=payload)


async def login_user(
    client: httpx.AsyncClient,
    username_or_email: str = "test_user",
    password: str = "SecurePass123!",
) -> httpx.Response:
    """Issue a real HTTP POST request to the login endpoint."""
    payload = {
        "email_or_username": username_or_email,
        "password": password,
    }
    return await client.post("/api/v1/login", json=payload)


async def create_db_user(
    session: AsyncSession,
    username: str = "admin_user",
    email: str = "admin_user@example.com",
    password: str = "AdminPass123!",
    role: str = "admin",
    full_name: str = "Admin User",
) -> User:
    """
    Directly create and persist a user entity in the test database.
    Essential for creating users with 'admin' role because the public
    registration route intentionally prohibits self-registering as admin.
    """
    user = User(
        id=uuid.uuid4(),
        username=username.strip(),
        full_name=full_name.strip(),
        email=email.strip().lower(),
        hashed_password=hash_password(password),
        role=role.strip().lower(),
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_headers(
    client: httpx.AsyncClient,
    session: AsyncSession,
    role: str = "viewer",
    username: str | None = None,
    email: str | None = None,
    password: str = "TestPass123!",
) -> dict[str, str]:
    """
    Helper to provision a user with the specified role and return authenticated headers.
    Avoids duplicated login and token generation across tests.
    """
    clean_role = role.lower().strip()
    u_name = username or f"{clean_role}_{uuid.uuid4().hex[:6]}"
    u_email = email or f"{u_name}@example.com"

    # Admin accounts cannot use public registration
    if clean_role == "admin":
        user = await create_db_user(
            session=session,
            username=u_name,
            email=u_email,
            password=password,
            role="admin",
            full_name=f"{u_name.title()} Admin",
        )
    else:
        reg_res = await register_user(
            client=client,
            username=u_name,
            email=u_email,
            password=password,
            role=clean_role,
            full_name=f"{u_name.title()} User",
        )
        assert reg_res.status_code == 201, f"User registration failed: {reg_res.text}"

    # Log in through HTTP endpoint to obtain token
    login_res = await login_user(client=client, username_or_email=u_name, password=password)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"

    token = login_res.json()["access_token"]
    return get_auth_headers(token)
