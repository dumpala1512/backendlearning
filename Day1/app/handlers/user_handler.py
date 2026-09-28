from app.schemas.user import AdminStatsResponse, UserResponse
from app.services import user_service


def get_me() -> UserResponse:
    """Return profile of the current logged-in user."""
    user = user_service.get_current_user()
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


def get_all_users() -> list[UserResponse]:
    """Return all users formatted as UserResponse models."""
    users = user_service.list_users()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            is_admin=u.is_admin,
            created_at=u.created_at,
        )
        for u in users
    ]


def get_admin_stats() -> AdminStatsResponse:
    """Return platform statistics for admins."""
    stats = user_service.get_admin_stats()
    return AdminStatsResponse(
        total_users=stats["total_users"],
        total_films=stats["total_films"],
        total_reviews=stats["total_reviews"],
        uptime_status=stats["uptime_status"],
    )
