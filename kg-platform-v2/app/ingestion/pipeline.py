"""Document ingestion pipeline with incremental / deduplication.

- Load PDF (or other supported formats) via ``load_pdf``.
- Chunk the raw text using ``chunk_text`` (size & overlap from config).
- For each chunk:
    * Check if the chunk has already been processed (Redis hash).
    * If new, extract KG entities/relations via ``extract_kg``.
    * Store the embedding vector via ``VectorStore.add_text`` (which now also deduplicates).
    * Upsert the extracted KG into Neo4j via ``upsert_graph``.
- All steps log their progress via the unified logger.

The pipeline can be invoked programmatically or via an API endpoint.
"""

import os
from ..core.config import get_settings
from typing import List

from ..core.logger import get_logger
from ..core.redis_client import RedisCache
from .document_loader import load_pdf
from .chunker import chunk_text
from .extractor import extract_kg
from ..rag.vector_store import VectorStore
from ..graph.graph_builder import upsert_graph
from ..core.incremental import is_chunk_processed, mark_chunk_processed, _hash_text

_logger = get_logger(__name__)


def enrich_entities_from_relations(kg: dict) -> dict:
    """Ensure every entity referenced in relations appears in ``kg['entities']``.

    If a name is missing, a placeholder entity with ``type='Unknown'`` and empty
    ``properties`` is added. Returns the enriched ``kg`` dict.
    """
    if not kg:
        return kg
    existing_names = {e.get("name") for e in kg.get("entities", [])}
    for rel in kg.get("relations", []):
        for key in ("from", "source", "to", "target"):
            name = rel.get(key)
            if name and name not in existing_names:
                kg.setdefault("entities", []).append(
                    {"name": name, "type": "Unknown", "properties": {}}
                )
                existing_names.add(name)
    return kg


def _process_chunk(chunk: str, store: VectorStore, chunk_id: str) -> None:
    """Process a single chunk: embed, store vector, extract KG, upsert graph.
    ``chunk_id`` is a deterministic hash used for logging.
    """
    # 1️⃣ Embed & store vector (deduplication handled inside add_text)
    key = f"chunk:{chunk_id}"
    added = store.add_text(key=key, text=chunk, metadata={"chunk_hash": chunk_id})
    if not added:
        _logger.info(f"Chunk {chunk_id[:8]} already stored - skipping KG extraction.")
        return

    # 2️⃣ Extract KG from the chunk
    kg = extract_kg(chunk)
    kg = enrich_entities_from_relations(kg)
    if not kg or not kg.get("entities"):
        _logger.info(f"No KG entities extracted from chunk {chunk_id[:8]}.")
        return

    # 3️⃣ Upsert into Neo4j
    try:
        upsert_graph(kg)
        _logger.info(f"Upserted KG from chunk {chunk_id[:8]} into Neo4j.")
    except Exception as e:
        _logger.error(f"Failed to upsert KG for chunk {chunk_id[:8]}: {e}")


def process_document(
    file_path: str, chunk_size: int = None, overlap: int = None
) -> None:
    """Full end‑to‑end processing of a document.

    Parameters
    ----------
    file_path: str
        Path to the PDF (or other supported) file.
    chunk_size, overlap: int, optional
        If omitted, values are taken from ``app.core.config.Settings``
        (defaults are larger for big files).
    """
    # Resolve runtime chunking parameters from settings if not supplied
    settings = get_settings()
    if chunk_size is None:
        chunk_size = getattr(settings, "CHUNK_SIZE", 4000)
    if overlap is None:
        overlap = getattr(settings, "CHUNK_OVERLAP", 200)
    if not os.path.isfile(file_path):
        _logger.error(f"Document not found: {file_path}")
        return

    # Load raw text (multi‑backend loader will pick best available parser)
    raw_text = load_pdf(file_path)
    # Ensure Unicode safety on Windows – drop characters that cannot be encoded with the default GBK codec
    raw_text = raw_text.encode("utf-8", errors="ignore").decode("utf-8")
    if not raw_text:
        _logger.error(f"Failed to extract text from: {file_path}")
        return

    # Chunking
    chunks = chunk_text(raw_text, size=chunk_size, overlap=overlap)
    _logger.info(f"Document split into {len(chunks)} chunks.")
    # Safety guard: limit number of chunks processed (avoid excessive embedding calls)
    max_chunks = getattr(settings, "MAX_CHUNKS", 2000)
    if len(chunks) > max_chunks:
        _logger.warning(
            f"Chunk count {len(chunks)} exceeds MAX_CHUNKS ({max_chunks}); truncating to first {max_chunks} chunks."
        )
        chunks = chunks[:max_chunks]

    # Prepare utilities
    redis_cache = RedisCache()
    vector_store = VectorStore()

    for chunk in chunks:
        # Deterministic hash for the chunk – used for dedup & logging
        chunk_hash = _hash_text(chunk)
        if is_chunk_processed(chunk, redis_cache):
            _logger.info(f"Chunk {chunk_hash[:8]} already processed - skipping.")
            continue
        _process_chunk(chunk, vector_store, chunk_hash)
        # Mark chunk as processed after successful handling (including failures)
        mark_chunk_processed(chunk, redis_cache)

    _logger.info("Document ingestion pipeline completed.")
