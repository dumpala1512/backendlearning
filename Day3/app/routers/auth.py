from fastapi import APIRouter, status
from app.handlers import auth_handler
from app.models.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserRegisterRequest) -> UserResponse:
    """Register a new user account with SecretStr password handling."""
    return auth_handler.register(payload=payload)


@router.post("/login", response_model=TokenResponse, summary="User login")
def login(payload: UserLoginRequest) -> TokenResponse:
    """Authenticate user credentials and receive access token."""
    return auth_handler.login(payload=payload)
