"""Simple Redis client wrapper for caching schema objects.

The wrapper lazily creates a connection based on settings defined in
``app.core.config.Settings``.  If Redis is unavailable (e.g., library missing or
cannot connect), all methods degrade to no‑ops so the rest of the system works
without Redis.
"""

import json
import os
from typing import Any, Optional

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

from .config import get_settings
from .logger import get_logger

_logger = get_logger(__name__)


class RedisCache:
    def __init__(self):
        self._client = None
        self._available = False
        if redis is None:
            _logger.warning("redis-py library not installed; RedisCache disabled.")
            return
        settings = get_settings()
        try:
            self._client = redis.StrictRedis(
                host=getattr(settings, "REDIS_HOST", "localhost"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                password=getattr(settings, "REDIS_PASSWORD", None),
                decode_responses=True,
            )
            # Simple ping to verify connection
            self._client.ping()
            self._available = True
        except Exception as e:
            _logger.warning(f"Redis connection failed: {e}; RedisCache disabled.")
            self._client = None
            self._available = False

    # ---------------------------------------------------------------------
    def get(self, key: str) -> Optional[Any]:
        if not self._available:
            return None
        try:
            raw = self._client.get(key)  # type: ignore
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            _logger.error(f"Redis get error for key {key}: {e}")
            return None

    # ---------------------------------------------------------------------
    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        """Store *value* (JSON serializable) under *key*.
        ``ex`` is optional expiry time in seconds.
        Returns ``True`` on success.
        """
        if not self._available:
            return False
        try:
            payload = json.dumps(value)
            self._client.set(key, payload, ex=ex)  # type: ignore
            return True
        except Exception as e:
            _logger.error(f"Redis set error for key {key}: {e}")
            return False

    # ---------------------------------------------------------------------
    def delete(self, key: str) -> bool:
        if not self._available:
            return False
        try:
            self._client.delete(key)  # type: ignore
            return True
        except Exception as e:
            _logger.error(f"Redis delete error for key {key}: {e}")
            return False
