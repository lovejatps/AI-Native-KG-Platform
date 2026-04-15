"""Utilities for incremental processing and deduplication.

The pipeline processes large documents (PDFs) in chunks.  To avoid re‑processing the same
chunk or re‑inserting the same vector/entity we use a deterministic SHA‑256 hash of the
chunk text as a unique identifier.

When Redis is available we store:
* `processed_chunk:<hash>` → sentinel (value `1`) to mark a chunk already processed.
* `embedding:<hash>` → the embedding vector (list of floats) to cache LLM embeddings.
* `entity_hash:<entity_name>` → optional mapping if you want to track which names have been
  already upserted (Neo4j MERGE already guarantees uniqueness on the `name` property).

If Redis is unavailable the functions degrade to in‑memory dictionaries, which are
persisted only for the current process run.
"""

import hashlib
from typing import Any, List

from .redis_client import RedisCache
from .logger import get_logger

_logger = get_logger(__name__)

# Global in‑memory fallbacks when Redis is not configured / unavailable
_processed_chunks: set[str] = set()
_embedding_cache: dict[str, List[float]] = {}


def _hash_text(text: str) -> str:
    """Return a hex SHA‑256 hash for *text*.
    Used as a deterministic identifier for deduplication.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_chunk_processed(chunk: str, cache: RedisCache | None = None) -> bool:
    """Check whether *chunk* has been processed before.
    Returns ``True`` if the hash is present in Redis (or in the in‑memory set).
    """
    h = _hash_text(chunk)
    if cache and cache._available:
        return cache.get(f"processed_chunk:{h}") is not None
    return h in _processed_chunks


def mark_chunk_processed(chunk: str, cache: RedisCache | None = None) -> None:
    """Mark *chunk* as processed.
    Stores the hash in Redis (or the in‑memory set) with a dummy value.
    """
    h = _hash_text(chunk)
    if cache and cache._available:
        cache.set(f"processed_chunk:{h}", 1)
    else:
        _processed_chunks.add(h)


def cache_embedding(
    text: str, vector: List[float], cache: RedisCache | None = None
) -> None:
    """Cache the *vector* for the given *text*.
    Stores the vector in Redis under ``embedding:<hash>``.
    """
    h = _hash_text(text)
    if cache and cache._available:
        cache.set(f"embedding:{h}", vector)
    else:
        _embedding_cache[h] = vector


def get_cached_embedding(
    text: str, cache: RedisCache | None = None
) -> List[float] | None:
    """Retrieve a cached embedding for *text* if present.
    Returns ``None`` when no cache hit.
    """
    h = _hash_text(text)
    if cache and cache._available:
        return cache.get(f"embedding:{h}")
    return _embedding_cache.get(h)
