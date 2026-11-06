from __future__ import annotations

import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.user import User
from tests.helpers import (
    get_auth_headers,
    login_user,
    register_user,
)


@pytest.mark.integration
async def test_registration_flow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Test 1 — Registration Flow
    Scenario:
    - register new user via HTTP POST request
    - verify success status and response schema
    - verify database contains new user and password is encrypted
    """
    # Arrange
    username = "clara_oswald"
    email = "clara.oswald@example.com"
    raw_password = "ImpossibleGirl2026!"
    payload = {
        "username": username,
        "email": email,
        "full_name": "Clara Oswald",
        "role": "viewer",
        "password": raw_password,
        "confirm_password": raw_password,
    }

    # Act: Issue real HTTP request directly through AsyncClient
    response = await client.post("/api/v1/register", json=payload)

    # Assert: Status code and response schema
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == username
    assert data["email"] == email
    assert data["role"] == "viewer"
    assert data["full_name"] == "Clara Oswald"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data

    user_id = uuid.UUID(data["id"])

    # Assert: Verify database persistence directly in isolated test database
    result = await db_session.execute(select(User).where(User.id == user_id))
    persisted_user = result.scalar_one_or_none()
    assert persisted_user is not None
    assert persisted_user.username == username
    assert persisted_user.email == email
    assert persisted_user.role == "viewer"

    # Assert: Verify password is encrypted/hashed and never stored in plaintext
    assert persisted_user.hashed_password != raw_password
    assert persisted_user.hashed_password.startswith("$2b$") or persisted_user.hashed_password.startswith("$2a$")
    assert verify_password(raw_password, persisted_user.hashed_password)


@pytest.mark.integration
async def test_login_flow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Test 2 — Login Flow
    Scenario:
    - login with registered user credentials
    Assertions:
    - success status code 200
    - access token exists and is valid
    - token type is bearer
    - expected JSON shape
    """
    # Arrange: Register a user first
    username = "amy_pond"
    email = "amy.pond@example.com"
    raw_password = "RoryWilliams123!"
    reg_response = await register_user(
        client=client,
        username=username,
        email=email,
        password=raw_password,
        role="viewer",
    )
    assert reg_response.status_code == 201

    # Act: Login via HTTP POST
    login_response = await login_user(
        client=client,
        username_or_email=username,
        password=raw_password,
    )

    # Assert: Success status and token response shape
    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20
    assert data["token_type"] == "bearer"
    assert "refresh_token" in data
    assert data["username"] == username
    assert data["role"] == "viewer"
    assert "user_id" in data


@pytest.mark.integration
async def test_authenticated_request(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Test 3 — Authenticated Request
    Scenario:
    - register & login to obtain access token
    - use returned token to call protected endpoint (GET /api/v1/users/me)
    Assertions:
    - request succeeds with status 200
    - authenticated user profile is returned correctly
    """
    # Arrange: Create user and login
    username = "rose_tyler"
    email = "rose.tyler@example.com"
    raw_password = "BadWolfPass123!"
    reg_res = await register_user(
        client=client,
        username=username,
        email=email,
        password=raw_password,
        role="critic",
    )
    assert reg_res.status_code == 201

    login_res = await login_user(client=client, username_or_email=email, password=raw_password)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = get_auth_headers(token)

    # Act: Call protected endpoint
    response = await client.get("/api/v1/users/me", headers=headers)

    # Assert: Status code and returned payload matches authenticated identity
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["username"] == username
    assert me_data["email"] == email
    assert me_data["role"] == "critic"
    assert "id" in me_data


@pytest.mark.integration
async def test_login_invalid_password(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify that login fails with 401 when invalid password is provided."""
    username = "martha_jones"
    email = "martha.jones@example.com"
    raw_password = "CorrectPass123!"

    reg_res = await register_user(client=client, username=username, email=email, password=raw_password)
    assert reg_res.status_code == 201

    # Act with incorrect password
    response = await login_user(client=client, username_or_email=username, password="WrongPassword999!")

    # Assert
    assert response.status_code == 401
    err = response.json()
    assert "error" in err or "message" in err or "detail" in err


@pytest.mark.integration
async def test_duplicate_registration_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify that registering with an existing username or email returns 409 Conflict."""
    username = "donna_noble"
    email = "donna.noble@example.com"
    password = "DonnaNoblePass123!"

    first = await register_user(client=client, username=username, email=email, password=password)
    assert first.status_code == 201

    # Duplicate username attempt
    second = await register_user(
        client=client,
        username=username,
        email="different.email@example.com",
        password=password,
    )
    assert second.status_code == 409


@pytest.mark.integration
async def test_unauthenticated_request_rejected(client: AsyncClient) -> None:
    """Verify that accessing protected endpoints without an Authorization header returns 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.integration
async def test_invalid_token_rejected(client: AsyncClient) -> None:
    """Verify that supplying a malformed or forged JWT returns 401."""
    bad_headers = {"Authorization": "Bearer this.is.not.a.valid.jwt.token"}
    response = await client.get("/api/v1/users/me", headers=bad_headers)
    assert response.status_code == 401


@pytest.mark.integration
async def test_public_registration_cannot_create_admin(client: AsyncClient) -> None:
    """Verify that public registration rejects attempts to register with role 'admin'."""
    payload = {
        "username": "hacker_admin",
        "email": "hacker@example.com",
        "password": "HackerPassword123!",
        "confirm_password": "HackerPassword123!",
        "role": "admin",
    }
    response = await client.post("/api/v1/register", json=payload)
    # FastApi / Pydantic validator will reject with 422 or route with 403
    assert response.status_code in (403, 422)
