from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_user_service
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register(
    payload: UserRegisterRequest,
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account with secure bcrypt password hashing and database persistence.
    Public endpoint. Passwords are never stored in plaintext and hashes are never returned.
    """
    user = await service.register(
        session=db,
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password.get_secret_value(),
        role=payload.role,
    )
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
)
@router.post(
    "/auth/login",
    response_model=TokenResponse,
    include_in_schema=False,
)
async def login(
    payload: UserLoginRequest,
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user credentials (username or email + password).
    On successful verification, issues both a short-lived access token and a
    longer-lived refresh token persisted server-side for replay protection.
    Public endpoint.
    """
    access_token, refresh_token, user = await service.login(
        session=db,
        username=payload.username,
        email=payload.email,
        password=payload.password.get_secret_value(),
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    include_in_schema=False,
)
async def refresh(
    payload: RefreshTokenRequest,
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Validate refresh token, reject expired or already-used tokens (single use replay protection),
    and issue a brand new access token.
    Public endpoint.
    """
    new_access_token = await service.refresh_access_token(
        session=db,
        refresh_token=payload.refresh_token,
    )
    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
    )
