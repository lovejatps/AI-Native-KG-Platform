"""Simple in‑memory user store for demonstration.

In a production system this would be replaced with a persistent storage
(e.g., SQLAlchemy models backed by Postgres). For Phase‑2 we only need a
functional login/registration flow to protect the API.
"""

from typing import Dict

from .utils import get_password_hash, verify_password

# ``_users`` maps email -> hashed password
_users: Dict[str, str] = {}


def create_user(email: str, password: str) -> bool:
    """Create a new user; returns ``True`` on success, ``False`` if already exists."""
    if email in _users:
        return False
    _users[email] = get_password_hash(password)
    return True


def authenticate_user(email: str, password: str) -> bool:
    """Validate credentials; returns ``True`` if they match an existing user."""
    hashed = _users.get(email)
    if not hashed:
        return False
    return verify_password(password, hashed)
