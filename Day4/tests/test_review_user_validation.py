import uuid
from unittest.mock import AsyncMock

import pytest

from app.exceptions.user import UserNotFoundError
from app.services.review_service import ReviewService


@pytest.mark.asyncio
async def test_add_review_rejects_unknown_user_before_database_insert() -> None:
    film_dao = AsyncMock()
    film_dao.get_by_id.return_value = object()
    user_dao = AsyncMock()
    user_dao.get_by_id.return_value = None
    review_dao = AsyncMock()
    user_id = uuid.uuid4()

    service = ReviewService(dao=review_dao, film_dao=film_dao, user_dao=user_dao)

    with pytest.raises(UserNotFoundError):
        await service.add_review(
            session=object(),
            film_id=uuid.uuid4(),
            rating=5,
            review="A review with enough text to pass the normal review length validation.",
            user_id=user_id,
        )

    review_dao.create.assert_not_awaited()
