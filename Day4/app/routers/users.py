from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.dependencies import get_db, get_user_service
from app.schemas.user import AdminStatsResponse, UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.get("/users/me", response_model=UserResponse, tags=["Users"], summary="Get current user profile")
async def get_current_user_profile(
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get profile information for the current user from PostgreSQL."""
    user = await service.get_current_user(session=db)
    if not user:
        raise UserNotFoundError("No user profile found. Please register or seed a user first.")
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse], tags=["Users"], summary="List all users")
async def list_all_users(
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """Get a list of all registered users from PostgreSQL."""
    users = await service.list_users(session=db, limit=50)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/admin/stats", response_model=AdminStatsResponse, tags=["Admin"], summary="Get platform statistics")
@router.get("/users/admin/stats", response_model=AdminStatsResponse, tags=["Admin"], include_in_schema=False)
async def get_admin_statistics(
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:
    """Get system-wide metrics and stats directly via DAO counts."""
    stats = await service.get_admin_stats(session=db)
    return AdminStatsResponse(
        total_users=int(stats["total_users"]),
        total_films=int(stats["total_films"]),
        total_reviews=int(stats["total_reviews"]),
        uptime_status=str(stats["uptime_status"]),
    )
