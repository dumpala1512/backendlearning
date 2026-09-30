from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import DatabaseSession, get_db
from app.handlers import auth_handler
from app.models.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserRegisterRequest,
    db: DatabaseSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account into PostgreSQL with real database persistence."""
    return await auth_handler.register(db=db, payload=payload)


@router.post("/login", response_model=TokenResponse, summary="User login")
async def login(
    payload: UserLoginRequest,
    db: DatabaseSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials against PostgreSQL and receive access token."""
    return await auth_handler.login(db=db, payload=payload)
