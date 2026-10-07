from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import UserNotFoundError
from app.dependencies import get_current_user, get_db, get_user_service
from app.schemas.user import AdminStatsResponse, AuthenticatedUser, UserResponse
from app.services.user_service import UserService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/users/me", response_model=UserResponse, tags=["Users"], summary="Get current user profile")
async def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get profile information for the authenticated current user from PostgreSQL."""
    user = await service.get_by_id(session=db, user_id=current_user.id)
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
