from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.exceptions.user import InvalidTokenError, TokenExpiredError

# Password hashing configuration using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt via passlib.
    The original password cannot be recovered.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Generate a signed JWT access token.
    Claims include sub (user id), username, role, type="access", iat, exp, and jti.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Ensure required claims
    to_encode.update(
        {
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": str(uuid.uuid4()),
        }
    )
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"]) 

    return jwt.encode(to_encode, settings.TOKEN_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    jti: str | None = None,
) -> str:
    """
    Generate a signed JWT refresh token.
    Claims include sub (user id), username, role, type="refresh", iat, exp, and jti.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    token_jti = jti or str(uuid.uuid4())
    to_encode.update(
        {
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": token_jti,
        }
    )
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    return jwt.encode(to_encode, settings.TOKEN_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """
    Decode and validate a JWT.
    Verifies signature, expiration, required claims, and optional token type.
    Raises typed AuthenticationError / InvalidTokenError / TokenExpiredError on failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.TOKEN_SECRET_KEY,
            algorithms=[ALGORITHM],
        )
    except ExpiredSignatureError:
        raise TokenExpiredError(message="Token has expired.")
    except JWTClaimsError as e:
        raise InvalidTokenError(message=f"Invalid token claims: {e}")
    except JWTError as e:
        raise InvalidTokenError(message=f"Could not validate token: {e}")

    # Validate required claims
    if "sub" not in payload:
        raise InvalidTokenError(message="Token payload is missing subject claim ('sub').")
    if "type" not in payload:
        raise InvalidTokenError(message="Token payload is missing type claim ('type').")

    token_type = payload.get("type")
    if expected_type is not None and token_type != expected_type:
        raise InvalidTokenError(
            message=f"Invalid token type. Expected '{expected_type}', got '{token_type}'."
        )

    return payload
