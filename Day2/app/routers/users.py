from fastapi import APIRouter
from app.handlers import user_handler
from app.models.user import AdminStatsResponse, UserResponse

router = APIRouter()


@router.get("/users/me", response_model=UserResponse, tags=["Users"], summary="Get current user profile")
def get_current_user_profile() -> UserResponse:
    """Get profile information for the current user."""
    return user_handler.get_me()


@router.get("/users", response_model=list[UserResponse], tags=["Users"], summary="List all users")
def list_all_users() -> list[UserResponse]:
    """Get a list of all registered users."""
    return user_handler.get_all_users()


@router.get("/admin/stats", response_model=AdminStatsResponse, tags=["Admin"], summary="Get platform statistics")
def get_admin_statistics() -> AdminStatsResponse:
    """Get system-wide metrics and stats for administrators."""
    return user_handler.get_admin_stats()
