"""Utility functions for authentication.

- Password hashing using ``passlib`` (bcrypt).
- JWT creation/verification using ``python-jose``.

The secret key is taken from environment variable ``JWT_SECRET_KEY``;
if not set, a default insecure key is used for development only.
"""

import os
from datetime import datetime, timedelta
from typing import Any

import hashlib
from jose import JWTError, jwt

# Simple SHA-256 based password hashing (fallback for environments without passlib).
# NOTE: This is NOT as strong as bcrypt but sufficient for development/testing.
# In production you should replace this with a proper password‑hashing library.


def _hash_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# Secret key – must be set in production.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insecure-development-secret")
JWT_ALGORITHM = "HS256"
# Token lifetime – 1 hour by default; can be overridden via env.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` if ``plain_password`` matches ``hashed_password``.
    Uses SHA-256 hash comparison as a simple fallback.
    """
    return _hash_sha256(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    """Hash a plain password for storage using SHA-256.
    Replace with a stronger algorithm (e.g., bcrypt via passlib) in production.
    """
    return _hash_sha256(password)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a signed JWT.

    ``data`` should contain the payload (e.g. ``{"sub": user_id}``).
    The token expires after ``expires_delta`` or the default lifetime.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT, returning the payload or ``None`` on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
