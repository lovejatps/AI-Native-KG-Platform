from .milvus_client import MilvusClient
from ..core.logger import get_logger

_logger = get_logger(__name__)


class VectorStore:
    def __init__(self):
        # Initialize Milvus client; collection will be created if missing
        self.client = MilvusClient()
        # Lazy import of embedding model – only needed for text‑to‑vector
        from ..core.embedding import EmbeddingModel

        self.embedder = EmbeddingModel()

    def add_vector(self, key, vector, metadata=None):
        """Add a vector to Milvus. The *key* is stored in metadata for lookup."""
        meta = {"key": key}
        if metadata:
            meta.update(metadata)
        self.client.add_vector(vector, metadata=meta)
        return True

    def add_text(self, key: str, text: str, metadata=None):
        """Embed *text* using the vLLM model with deduplication and store the vector.
        Returns ``True`` if a new vector was stored, ``False`` when the chunk was already processed.
        """
        # Incremental utilities – cache processed chunks & embeddings via Redis (fallback to in‑memory)
        from ..core.incremental import (
            is_chunk_processed,
            mark_chunk_processed,
            get_cached_embedding,
            cache_embedding,
            _hash_text,
        )
        from ..core.redis_client import RedisCache

        redis_cache = RedisCache()
        # 1️⃣ Skip if this chunk/text was already processed
        if is_chunk_processed(text, redis_cache):
            _logger.info(
                f"Chunk already processed (hash={_hash_text(text)[:8]}). Skipping add_text."
            )
            return False

        # 2️⃣ Try to reuse a cached embedding first
        vector = get_cached_embedding(text, redis_cache)
        if vector is None:
            vectors = self.embedder.embed([text])
            if not vectors:
                return False
            vector = vectors[0]
            # Cache embedding for future calls
            cache_embedding(text, vector, redis_cache)

        # 3️⃣ Store the vector in Milvus (or fallback store)
        added = self.add_vector(key=key, vector=vector, metadata=metadata)
        # 4️⃣ Mark the chunk as processed to avoid re‑embedding later
        mark_chunk_processed(text, redis_cache)
        return added

    def search(self, vector, top_k: int = 5):
        """Search similar vectors using Milvus and return stored metadata."""
        results = self.client.search(vector, top_k=top_k)
        # Return list of (key, distance, metadata)
        return [
            (r["metadata"].get("key"), r["distance"], r["metadata"]) for r in results
        ]
