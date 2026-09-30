from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import DatabaseSession, get_db
from app.handlers import user_handler
from app.models.user import AdminStatsResponse, UserResponse

router = APIRouter()


@router.get("/users/me", response_model=UserResponse, tags=["Users"], summary="Get current user profile")
async def get_current_user_profile(
    db: DatabaseSession = Depends(get_db),
) -> UserResponse:
    """Get profile information for the current user from PostgreSQL."""
    return await user_handler.get_me(db=db)


@router.get("/users", response_model=list[UserResponse], tags=["Users"], summary="List all users")
async def list_all_users(
    db: DatabaseSession = Depends(get_db),
) -> list[UserResponse]:
    """Get a list of all registered users from PostgreSQL."""
    return await user_handler.get_all_users(db=db)


@router.get("/admin/stats", response_model=AdminStatsResponse, tags=["Admin"], summary="Get platform statistics")
async def get_admin_statistics(
    db: DatabaseSession = Depends(get_db),
) -> AdminStatsResponse:
    """Get system-wide metrics and stats directly from PostgreSQL via SQLAlchemy counts."""
    return await user_handler.get_admin_stats(db=db)
