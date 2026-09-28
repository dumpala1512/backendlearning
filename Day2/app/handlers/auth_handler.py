from fastapi import HTTPException, status
from app.models.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services import user_service


def register(payload: UserRegisterRequest) -> UserResponse:
    """Register a new user account using SecretStr for password confidentiality."""
    try:
        user = user_service.register(
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


def login(payload: UserLoginRequest) -> TokenResponse:
    """Authenticate user credentials and return bearer token."""
    token = user_service.login(
        username=payload.username,
        password=payload.password.get_secret_value(),
    )
    return TokenResponse(access_token=token, token_type="bearer")
