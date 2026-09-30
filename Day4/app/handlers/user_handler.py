from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AdminStatsResponse, UserResponse
from app.services import user_service


async def get_me(db: AsyncSession) -> UserResponse:
    """Return profile of current logged-in user from PostgreSQL."""
    user = await user_service.get_current_user(db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user profile found. Please register a user first.",
        )
    return UserResponse.model_validate(user)


async def get_all_users(db: AsyncSession) -> list[UserResponse]:
    """Return all users formatted as UserResponse models."""
    users = await user_service.list_users(db=db)
    return [UserResponse.model_validate(u) for u in users]


async def get_admin_stats(db: AsyncSession) -> AdminStatsResponse:
    """Return platform statistics for admins querying real database counts."""
    stats = await user_service.get_admin_stats(db=db)
    return AdminStatsResponse.model_validate(stats)
