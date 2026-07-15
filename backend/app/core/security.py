from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import uuid

import bcrypt
import jwt

from app.core.config import settings
from app.exceptions.base import ValidationException


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed database value."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Computes a cryptographically secure bcrypt hash for a plain text password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token containing the subject identifier."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT refresh token containing the subject identifier."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh", "jti": str(uuid.uuid4())}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def validate_password_strength(password: str) -> None:
    """
    Enforces the platform's strong password policy rules.
    Raises a ValidationException if rules are not satisfied.
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        raise ValidationException(message=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.")
    if not any(char.isupper() for char in password):
        raise ValidationException(message="Password must contain at least one uppercase letter.")
    if not any(char.islower() for char in password):
        raise ValidationException(message="Password must contain at least one lowercase letter.")
    if not any(char.isdigit() for char in password):
        raise ValidationException(message="Password must contain at least one digit.")

    special_chars = "!@#$%^&*()-_=+[]{}|;:',.<>?/~`"
    if not any(char in special_chars for char in password):
        raise ValidationException(message="Password must contain at least one special character.")
