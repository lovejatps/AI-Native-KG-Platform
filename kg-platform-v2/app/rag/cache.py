"""Simple in‑memory cache for RAG query results.

This is a lightweight placeholder – production should use Redis or a
persistent cache. The cache stores the result of a query string for the
configured ``CACHE_TTL`` seconds.
"""

import time
from typing import Any, Dict

CACHE_TTL = int(os.getenv("RAG_CACHE_TTL", "300"))  # default 5 minutes

_cache_store: Dict[str, Dict[str, Any]] = {}


def get_cached(query: str) -> Any | None:
    entry = _cache_store.get(query)
    if not entry:
        return None
    if time.time() - entry["ts"] > CACHE_TTL:
        # expired
        del _cache_store[query]
        return None
    return entry["value"]


def set_cached(query: str, value: Any) -> None:
    _cache_store[query] = {"value": value, "ts": time.time()}
