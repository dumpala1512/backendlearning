from fastapi import HTTPException, status
from app.schemas.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services import user_service


def register(payload: UserRegisterRequest) -> UserResponse:
    """Handle user registration."""
    try:
        user = user_service.register(
            username=payload.username,
            email=payload.email,
            password=payload.password,
        )
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


def login(payload: UserLoginRequest) -> TokenResponse:
    """Handle user login and token generation."""
    token = user_service.login(
        username=payload.username,
        password=payload.password,
    )
    return TokenResponse(access_token=token, token_type="bearer")
