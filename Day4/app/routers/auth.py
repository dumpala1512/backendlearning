from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_user_service
from app.schemas.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegisterRequest,
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account with real database persistence.
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
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


@router.post("/login", response_model=TokenResponse, summary="User login")
async def login(
    payload: UserLoginRequest,
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user credentials against database and receive access token.
    Follows: Route -> Service -> DAO -> AsyncSession -> Database.
    """
    try:
        token = await service.login(
            session=db,
            username=payload.username,
            password=payload.password.get_secret_value(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )
