from app.models.user import AdminStatsResponse, UserResponse
from app.services import user_service


def get_me() -> UserResponse:
    """Return profile of the current logged-in user."""
    user = user_service.get_current_user()
    return UserResponse.model_validate(user)


def get_all_users() -> list[UserResponse]:
    """Return all users formatted as UserResponse models using from_attributes."""
    users = user_service.list_users()
    return [UserResponse.model_validate(u) for u in users]


def get_admin_stats() -> AdminStatsResponse:
    """Return platform statistics for admins."""
    stats = user_service.get_admin_stats()
    return AdminStatsResponse(**stats)
