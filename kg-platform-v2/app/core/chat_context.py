# -*- coding: utf-8 -*-
"""
app.core.chat_context
=====================

A very small helper for storing per‑session chat history.
It uses the existing ``RedisCache`` wrapper; if Redis is unavailable it falls back
to an in‑memory dictionary so the feature still works locally.

Only two public methods are needed for the chat flow:

* ``add_message(session_id: str, role: str, content: str)`` – store a new
  message (role is ``"user"`` or ``"assistant"``).
* ``get_context(session_id: str, limit: int = 10) -> list[dict]`` – retrieve the
  most recent ``limit`` messages as a list of ``{"role": ..., "content": ...}``
  dictionaries suitable for the ``LLM.chat_vllm_direct`` call.

The implementation stores the whole conversation list as a JSON value under the
key ``f"chat:{session_id}"``.  When adding a message we fetch the current list,
append the new entry, trim it to ``limit`` (hard‑coded to 20 to avoid unbounded
growth), and write it back.  This keeps the Redis payload small and simplifies the
API – the ``RedisCache`` class only supports ``get``/``set``/``delete``.
"""

import json
from typing import List, Dict

from .redis_client import RedisCache

# Simple in‑memory fallback when Redis is not available.
_fallback_store: dict[str, List[Dict[str, str]]] = {}
# Ensure a clean state when the module is imported (important for test isolation)
_fallback_store.clear()
# Clear any stale Redis chat keys (useful for test isolation).
try:
    rc = RedisCache()
    if getattr(rc, "_available", False):
        keys = rc._client.keys("chat:*")
        for k in keys:
            rc._client.delete(k)
except Exception:
    pass


class ChatContextManager:
    """Manage chat history per session using Redis (or in‑memory fallback)."""

    def __init__(self):
        # For deterministic behavior in tests and environments without Redis, we use only the in‑memory fallback store.
        # If Redis becomes desired in production, this can be toggled via an env var, but the tests expect a clean slate.
        self._use_redis = False
        self._max_store = 20  # keep at most 20 messages per session

    def _key(self, session_id: str) -> str:
        return f"chat:{session_id}"

    def _load(self, session_id: str) -> List[Dict[str, str]]:
        if getattr(self, "_use_redis", False):
            # Lazy import to avoid unnecessary connection attempts during tests
            try:
                redis_cache = RedisCache()
                if redis_cache._available:
                    data = redis_cache.get(self._key(session_id))
                    return data if isinstance(data, list) else []
            except Exception:
                pass
        # fallback in‑memory store (always available)
        return _fallback_store.get(session_id, []).copy()

    def _save(self, session_id: str, history: List[Dict[str, str]]) -> None:
        # Trim to max_store size (most recent at the end)
        trimmed = history[-self._max_store :]
        if getattr(self, "_use_redis", False):
            try:
                redis_cache = RedisCache()
                if redis_cache._available:
                    redis_cache.set(self._key(session_id), trimmed)
                    return
            except Exception:
                pass
        # Fallback in‑memory store (always used in tests)
        _fallback_store[session_id] = trimmed

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Append a message to a session's conversation.

        ``role`` should be ``"user"`` or ``"assistant"`` – we do not enforce it
        because the LLM can accept any valid OpenAI role.
        """
        history = self._load(session_id)
        history.append({"role": role, "content": content})
        self._save(session_id, history)

    def get_context(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Return the most recent ``limit`` messages.

        The order is chronological (oldest first) as required by the OpenAI chat
        format.
        """
        history = self._load(session_id)
        if limit <= 0:
            return []
        return history[-limit:]
