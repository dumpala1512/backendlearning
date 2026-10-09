from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions.user import AuthenticationError, InvalidTokenError, TokenExpiredError
from app.models.user import User


# ==============================================================================
# 1. Password Security & Hashing Tests
# ==============================================================================
def test_password_hashing_and_verification():
    """Verify bcrypt password hashing and verification helpers."""
    plain = "SuperSecretPassword123!"
    hashed = hash_password(plain)

    # Hash should not be plaintext
    assert hashed != plain
    assert hashed.startswith("$2b$")

    # Correct password verifies
    assert verify_password(plain, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword!", hashed) is False

    # Two hashes of the same password should differ (random salt)
    second_hash = hash_password(plain)
    assert hashed != second_hash
    assert verify_password(plain, second_hash) is True


# ==============================================================================
# 2. JWT Creation & Validation Tests
# ==============================================================================
def test_jwt_access_and_refresh_token_claims():
    """Verify JWT access and refresh token claims, signing, and types."""
    user_id = str(uuid.uuid4())
    token_data = {
        "sub": user_id,
        "username": "cinephile99",
        "role": "critic",
    }

    # Access token
    access_tok = create_access_token(token_data)
    decoded_access = decode_token(access_tok, expected_type="access")
    assert decoded_access["sub"] == user_id
    assert decoded_access["username"] == "cinephile99"
    assert decoded_access["role"] == "critic"
    assert decoded_access["type"] == "access"
    assert "iat" in decoded_access
    assert "exp" in decoded_access
    assert decoded_access["exp"] > decoded_access["iat"]

    # Refresh token
    refresh_tok = create_refresh_token(token_data)
    decoded_refresh = decode_token(refresh_tok, expected_type="refresh")
    assert decoded_refresh["sub"] == user_id
    assert decoded_refresh["username"] == "cinephile99"
    assert decoded_refresh["role"] == "critic"
    assert decoded_refresh["type"] == "refresh"

    # Access token rejected when expected_type is refresh
    with pytest.raises(InvalidTokenError) as exc_info:
        decode_token(access_tok, expected_type="refresh")
    assert "Invalid token type" in str(exc_info.value)

    # Refresh token rejected when expected_type is access
    with pytest.raises(InvalidTokenError) as exc_info:
        decode_token(refresh_tok, expected_type="access")
    assert "Invalid token type" in str(exc_info.value)


def test_jwt_expired_token_rejection():
    """Verify that expired tokens are cleanly rejected with TokenExpiredError."""
    user_id = str(uuid.uuid4())
    # Create token already expired 10 minutes ago
    expired_token = create_access_token(
        data={"sub": user_id, "username": "expired_user"},
        expires_delta=timedelta(minutes=-10),
    )

    with pytest.raises(TokenExpiredError):
        decode_token(expired_token)


def test_jwt_invalid_signature_and_malformed():
    """Verify that malformed or tampered tokens are rejected."""
    # Malformed token
    with pytest.raises(InvalidTokenError):
        decode_token("not-a-valid-jwt-token")

    # Tampered signature
    valid_token = create_access_token({"sub": "user-123", "username": "u"})
    tampered_token = valid_token[:-4] + "abcd"
    with pytest.raises(InvalidTokenError):
        decode_token(tampered_token)


# ==============================================================================
# 3. HTTP Endpoints: /register, /login, /refresh Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_register_flow(client: AsyncClient, db_session: AsyncSession):
    """
    POST /register:
    - validates request
    - ensures unique username & email
    - hashes password securely
    - never returns password or password hash
    """
    payload = {
        "username": "alice_wonder",
        "email": "alice@example.com",
        "password": "Password123!",
        "full_name": "Alice Wonderland",
    }
    res = await client.post("/api/v1/register", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == "alice_wonder"
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice Wonderland"
    assert "password" not in body
    assert "hashed_password" not in body
    assert "id" in body

    # Duplicate username returns 409
    dup_user_res = await client.post(
        "/api/v1/register",
        json={
            "username": "alice_wonder",
            "email": "different@example.com",
            "password": "Password123!",
        },
    )
    assert dup_user_res.status_code == 409

    # Duplicate email returns 409
    dup_email_res = await client.post(
        "/api/v1/register",
        json={
            "username": "different_user",
            "email": "alice@example.com",
            "password": "Password123!",
        },
    )
    assert dup_email_res.status_code == 409

    # Null fullname must raise an error (422)
    null_fullname_res = await client.post(
        "/api/v1/register",
        json={
            "username": "null_name_user",
            "email": "null_name@example.com",
            "password": "Password123!",
            "fullname": None,
        },
    )
    assert null_fullname_res.status_code == 422
    assert "Full name cannot be null" in null_fullname_res.text

    # Null full_name must raise an error (422)
    null_full_name_res = await client.post(
        "/api/v1/register",
        json={
            "username": "null_name_user_2",
            "email": "null_name2@example.com",
            "password": "Password123!",
            "full_name": None,
        },
    )
    assert null_full_name_res.status_code == 422
    assert "Full name cannot be null" in null_full_name_res.text


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient):
    """
    POST /login:
    - login with username succeeds
    - login with email succeeds
    - returns both access_token and refresh_token
    - invalid credentials rejected with 401
    """
    # Register user
    reg_payload = {
        "username": "bob_builder",
        "email": "bob@example.com",
        "password": "CanWeFixIt123!",
    }
    reg_res = await client.post("/api/v1/register", json=reg_payload)
    assert reg_res.status_code == 201

    # Login with username
    login_user_res = await client.post(
        "/api/v1/login",
        json={"username": "bob_builder", "password": "CanWeFixIt123!"},
    )
    assert login_user_res.status_code == 200
    tokens = login_user_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["username"] == "bob_builder"

    # Login with email
    login_email_res = await client.post(
        "/api/v1/login",
        json={"email": "bob@example.com", "password": "CanWeFixIt123!"},
    )
    assert login_email_res.status_code == 200
    assert "access_token" in login_email_res.json()

    # Login with email in username field
    login_email_as_username_res = await client.post(
        "/api/v1/login",
        json={"username": "bob@example.com", "password": "CanWeFixIt123!"},
    )
    assert login_email_as_username_res.status_code == 200
    assert "access_token" in login_email_as_username_res.json()

    # Login with username and empty string email (neither requires the other)
    login_empty_email_res = await client.post(
        "/api/v1/login",
        json={"username": "bob_builder", "email": "", "password": "CanWeFixIt123!"},
    )
    assert login_empty_email_res.status_code == 200
    assert "access_token" in login_empty_email_res.json()

    # Login with email and empty string username (neither requires the other)
    login_empty_user_res = await client.post(
        "/api/v1/login",
        json={"username": "", "email": "bob@example.com", "password": "CanWeFixIt123!"},
    )
    assert login_empty_user_res.status_code == 200
    assert "access_token" in login_empty_user_res.json()

    # Login using identifier alias
    login_identifier_res = await client.post(
        "/api/v1/login",
        json={"identifier": "bob_builder", "password": "CanWeFixIt123!"},
    )
    assert login_identifier_res.status_code == 200
    # Login using email_or_username field
    login_email_or_user_res = await client.post(
        "/api/v1/login",
        json={"email_or_username": "bob_builder", "password": "CanWeFixIt123!"},
    )
    assert login_email_or_user_res.status_code == 200
    assert "access_token" in login_email_or_user_res.json()

    # Neither username nor email provided -> 422 Unprocessable Entity
    neither_res = await client.post(
        "/api/v1/login",
        json={"password": "CanWeFixIt123!"},
    )
    assert neither_res.status_code == 422

    # Wrong password -> 401
    bad_pwd_res = await client.post(
        "/api/v1/login",
        json={"username": "bob_builder", "password": "WrongPassword!"},
    )
    assert bad_pwd_res.status_code == 401
    assert bad_pwd_res.json()["type"] == "InvalidCredentials"

    # Non-existent user -> 401
    bad_user_res = await client.post(
        "/api/v1/login",
        json={"username": "non_existent_user_999", "password": "AnyPassword!"},
    )
    assert bad_user_res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient):
    """
    POST /api/v1/refresh:
    - validates refresh token statelessly
    - issues a brand new access token
    - rejects access token mistakenly sent as refresh token
    """
    # Register and login
    await client.post(
        "/api/v1/register",
        json={"username": "carol_danvers", "email": "carol@marvel.com", "password": "HigherFurtherFaster1!"},
    )
    login_res = await client.post(
        "/api/v1/login",
        json={"username": "carol_danvers", "password": "HigherFurtherFaster1!"},
    )
    assert login_res.status_code == 200
    initial_tokens = login_res.json()
    refresh_token = initial_tokens["refresh_token"]
    old_access_token = initial_tokens["access_token"]

    # First refresh: successfully issues new access token
    refresh_res = await client.post(
        "/api/v1/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "access_token" in new_data

    # Subsequent refresh: also succeeds statelessly with valid refresh token
    second_res = await client.post(
        "/api/v1/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second_res.status_code == 200
    assert "access_token" in second_res.json()

    # Reject access token passed to /api/v1/refresh
    wrong_type_res = await client.post(
        "/api/v1/refresh",
        json={"refresh_token": old_access_token},
    )
    assert wrong_type_res.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_expired_rejection(client: AsyncClient):
    """Verify expired refresh token is rejected with 401."""
    expired_refresh = create_refresh_token(
        data={"sub": str(uuid.uuid4()), "username": "exp_user"},
        expires_delta=timedelta(days=-1),
    )
    res = await client.post("/api/v1/refresh", json={"refresh_token": expired_refresh})
    assert res.status_code == 401
    assert res.json()["type"] == "TokenExpired"


# ==============================================================================
# 4. Protected Endpoints & Dependency Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_protected_endpoints_require_authentication(client: AsyncClient):
    """
    Verify that all non-public endpoints require Bearer authentication:
    - Missing Authorization header -> 401
    - Invalid/malformed token -> 401
    - Expired access token -> 401
    - Refresh token used as access token -> 401
    - Valid access token -> 200
    """
    # 1. Unauthenticated request to /api/v1/films
    no_auth_res = await client.get("/api/v1/films")
    assert no_auth_res.status_code == 401
    assert "Authorization header is missing" in no_auth_res.json()["message"]

    # 2. Invalid/Malformed Bearer token
    bad_token_res = await client.get(
        "/api/v1/films",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert bad_token_res.status_code == 401

    # 3. Expired access token
    expired_tok = create_access_token(
        {"sub": str(uuid.uuid4()), "username": "test_user"},
        expires_delta=timedelta(minutes=-5),
    )
    expired_res = await client.get(
        "/api/v1/films",
        headers={"Authorization": f"Bearer {expired_tok}"},
    )
    assert expired_res.status_code == 401
    assert expired_res.json()["type"] == "TokenExpired"

    # 4. Refresh token sent as Bearer access token -> rejected
    refresh_tok = create_refresh_token({"sub": str(uuid.uuid4()), "username": "test_user"})
    wrong_type_res = await client.get(
        "/api/v1/films",
        headers={"Authorization": f"Bearer {refresh_tok}"},
    )
    assert wrong_type_res.status_code == 401
    assert "Invalid token type" in wrong_type_res.json()["message"]

    # 5. Valid access token succeeds
    valid_tok = create_access_token({"sub": str(uuid.uuid4()), "username": "test_user", "role": "user"})
    valid_res = await client.get(
        "/api/v1/films",
        headers={"Authorization": f"Bearer {valid_tok}"},
    )
    assert valid_res.status_code == 200


@pytest.mark.asyncio
async def test_users_me_profile_with_auth(client: AsyncClient):
    """Verify GET /api/v1/users/me returns authenticated user profile."""
    # Register user
    reg_payload = {
        "username": "profile_user",
        "email": "profile@example.com",
        "password": "ProfilePassword123!",
        "full_name": "Profile Owner",
    }
    reg_res = await client.post("/api/v1/register", json=reg_payload)
    assert reg_res.status_code == 201

    # Login
    login_res = await client.post(
        "/api/v1/login",
        json={"username": "profile_user", "password": "ProfilePassword123!"},
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]

    # Get /api/v1/users/me
    me_res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["username"] == "profile_user"
    assert profile["email"] == "profile@example.com"
    assert profile["full_name"] == "Profile Owner"
    assert "password" not in profile


@pytest.mark.asyncio
async def test_public_endpoints_accessible_without_auth(client: AsyncClient):
    """Verify /health and auth endpoints remain public."""
    # Health check is public
    health_res = await client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
