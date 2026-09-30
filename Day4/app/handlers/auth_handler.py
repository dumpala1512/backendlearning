from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services import user_service


async def register(db: AsyncSession, payload: UserRegisterRequest) -> UserResponse:
    """Register a new user account using SecretStr for password confidentiality."""
    try:
        user = await user_service.register(
            db=db,
            username=payload.username,
            email=payload.email,
            password=payload.password.get_secret_value(),
            role=payload.role,
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


async def login(db: AsyncSession, payload: UserLoginRequest) -> TokenResponse:
    """Authenticate user credentials and return bearer token."""
    try:
        token = await user_service.login(
            db=db,
            username=payload.username,
            password=payload.password.get_secret_value(),
        )
        return TokenResponse(access_token=token, token_type="bearer")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
