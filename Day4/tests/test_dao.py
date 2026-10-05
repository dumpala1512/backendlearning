from __future__ import annotations

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.film_dao import FilmDAO
from app.dao.review_dao import ReviewDAO
from app.dao.user_dao import UserDAO
from app.models.film import Film
from app.models.review import Review
from app.models.user import User


@pytest.mark.asyncio
async def test_film_dao_crud_and_soft_delete(db_session: AsyncSession):
    dao = FilmDAO()

    # 1. Create Film
    film = await dao.create(
        session=db_session,
        title="Inception",
        director="Christopher Nolan",
        release_year=2010,
        genre="Sci-Fi",
        description="A mind-bending thriller.",
    )
    assert isinstance(film.id, uuid.UUID)
    assert film.title == "Inception"
    assert film.is_active is True

    # 2. Get Film by ID
    found = await dao.get_by_id(session=db_session, film_id=film.id)
    assert found is not None
    assert found.title == "Inception"

    # Missing Film should return None without error
    missing = await dao.get_by_id(session=db_session, film_id=uuid.uuid4())
    assert missing is None

    # 3. List Films with dynamic filters
    await dao.create(
        session=db_session,
        title="Interstellar",
        director="Christopher Nolan",
        release_year=2014,
        genre="Sci-Fi",
    )
    await dao.create(
        session=db_session,
        title="The Godfather",
        director="Francis Ford Coppola",
        release_year=1972,
        genre="Crime",
    )

    all_films = await dao.list_films(session=db_session)
    assert len(all_films) == 3

    sci_fi = await dao.list_films(session=db_session, genre="Sci-Fi")
    assert len(sci_fi) == 2

    year_filtered = await dao.list_films(session=db_session, year_from=2012, year_to=2015)
    assert len(year_filtered) == 1
    assert year_filtered[0].title == "Interstellar"

    # 4. Update Film
    updated = await dao.update(session=db_session, film_id=film.id, description="Updated dream world description")
    assert updated is not None
    assert updated.description == "Updated dream world description"
    assert updated.title == "Inception"

    # 5. Soft Delete Film
    soft_deleted = await dao.soft_delete(session=db_session, film_id=film.id)
    assert soft_deleted is True
    # Row still exists, but is_active is False
    film_refreshed = await dao.get_by_id(session=db_session, film_id=film.id, active_only=False)
    assert film_refreshed is not None
    assert film_refreshed.is_active is False

    # Default get_by_id returns None for soft-deleted film
    assert await dao.get_by_id(session=db_session, film_id=film.id) is None

    # list_films excludes soft-deleted films
    remaining_films = await dao.list_films(session=db_session)
    assert len(remaining_films) == 2
    assert all(f.id != film.id for f in remaining_films)

    # count excludes soft-deleted films
    assert await dao.count(session=db_session) == 2

    # Soft delete on already soft-deleted or non-existent film returns False
    assert await dao.soft_delete(session=db_session, film_id=film.id) is False
    assert await dao.soft_delete(session=db_session, film_id=uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_review_dao_methods(db_session: AsyncSession):
    film_dao = FilmDAO()
    review_dao = ReviewDAO()

    film = await film_dao.create(
        session=db_session,
        title="The Dark Knight",
        director="Christopher Nolan",
        release_year=2008,
        genre="Action",
    )

    # 1. Create Reviews
    r1 = await review_dao.create(
        session=db_session,
        film_id=film.id,
        rating=9,
        review="Spectacular superhero movie with incredible performances.",
        reviewer_display_name="Alice Critic",
    )
    r2 = await review_dao.create(
        session=db_session,
        film_id=film.id,
        rating=10,
        review="Absolute cinematic masterpiece, Heath Ledger was unmatched.",
        reviewer_display_name="Bob Reviewer",
    )
    assert isinstance(r1.id, uuid.UUID)
    assert isinstance(r2.id, uuid.UUID)

    # 2. List Reviews (newest first)
    reviews = await review_dao.list_reviews(session=db_session, film_id=film.id)
    assert len(reviews) == 2
    assert reviews[0].id == r2.id  # newest first
    assert reviews[1].id == r1.id

    # 3. Average Rating
    avg = await review_dao.average_rating(session=db_session, film_id=film.id)
    assert avg == 9.5

    # Average for film without reviews
    empty_avg = await review_dao.average_rating(session=db_session, film_id=uuid.uuid4())
    assert empty_avg is None

    # 4. Delete Review
    deleted = await review_dao.delete(session=db_session, review_id=r1.id)
    assert deleted is True
    assert await review_dao.get_by_id(session=db_session, review_id=r1.id) is None

    # Delete non-existent review returns False
    assert await review_dao.delete(session=db_session, review_id=uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_user_dao_methods(db_session: AsyncSession):
    user_dao = UserDAO()

    # 1. Create User
    user = await user_dao.create(
        session=db_session,
        username="cinemafan",
        full_name="Cinema Fanatic",
        email="fan@cinema.org",
        hashed_password="hashed_secret_pw",
        role="critic",
    )
    assert isinstance(user.id, uuid.UUID)
    assert user.username == "cinemafan"
    assert user.full_name == "Cinema Fanatic"

    # 2. Get by email
    found_email = await user_dao.get_by_email(session=db_session, email="fan@cinema.org")
    assert found_email is not None
    assert found_email.id == user.id
    assert found_email.full_name == "Cinema Fanatic"

    missing_email = await user_dao.get_by_email(session=db_session, email="unknown@domain.com")
    assert missing_email is None

    # 3. Get by ID
    found_id = await user_dao.get_by_id(session=db_session, user_id=user.id)
    assert found_id is not None
    assert found_id.username == "cinemafan"

    # 4. Get by username
    found_username = await user_dao.get_by_username(session=db_session, username="cinemafan")
    assert found_username is not None
    assert found_username.email == "fan@cinema.org"

    # 5. Count
    total = await user_dao.count(session=db_session)
    assert total >= 1
