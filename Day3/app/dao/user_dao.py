from app.models.user import User

# Simple in-memory database for users
users_db: dict[int, User] = {
    1: User(
        id=1,
        username="admin",
        email="admin@example.com",
        hashed_password="mock_hashed_secret",
        role="admin",
    ),
    2: User(
        id=2,
        username="filmfan",
        email="filmfan@example.com",
        hashed_password="mock_hashed_password",
        role="user",
    ),
}

_next_id = 3


def get_by_id(user_id: int) -> User | None:
    """Find user by numeric ID."""
    return users_db.get(user_id)


def get_by_username(username: str) -> User | None:
    """Find user by username."""
    for user in users_db.values():
        if user.username.lower() == username.lower():
            return user
    return None


def get_by_email(email: str) -> User | None:
    """Find user by email address."""
    for user in users_db.values():
        if user.email.lower() == email.lower():
            return user
    return None


def create(username: str, email: str, hashed_password: str, role: str = "user") -> User:
    """Add a new user to the database."""
    global _next_id
    new_user = User(
        id=_next_id,
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role,
    )
    users_db[_next_id] = new_user
    _next_id += 1
    return new_user


def get_all() -> list[User]:
    """Get all users in the database."""
    return list(users_db.values())


def count() -> int:
    """Return total number of users."""
    return len(users_db)
