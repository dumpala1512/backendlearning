from app.dao import film_dao, review_dao, user_dao
from app.models.user import User


def register(username: str, email: str, password: str) -> User:
    """Register a new user account with basic validation."""
    if user_dao.get_by_username(username):
        raise ValueError(f"Username '{username}' is already taken.")
    if user_dao.get_by_email(email):
        raise ValueError(f"Email '{email}' is already registered.")

    return user_dao.create(
        username=username.strip(),
        email=email.strip().lower(),
        hashed_password=f"hash_{password}",
        is_admin=False,
    )


def login(username: str, password: str) -> str:
    """Mock login check returning an access token."""
    return f"mock_jwt_token_for_{username}"


def get_current_user() -> User:
    """Return default logged in demo user."""
    user = user_dao.get_by_id(1)
    if not user:
        user = User(
            id=1,
            username="demouser",
            email="demouser@example.com",
            hashed_password="mock",
            is_admin=False,
        )
    return user


def list_users() -> list[User]:
    """Return all users from the database."""
    return user_dao.get_all()


def get_admin_stats() -> dict:
    """Aggregate high-level platform statistics."""
    return {
        "total_users": user_dao.count(),
        "total_films": film_dao.count(),
        "total_reviews": review_dao.count(),
        "uptime_status": "healthy",
    }
