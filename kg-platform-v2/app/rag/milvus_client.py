try:
    from pymilvus import (
        Collection,
        connections,
        FieldSchema,
        CollectionSchema,
        DataType,
        utility,
    )
except Exception:
    # Fallback stub when pymilvus is unavailable
    Collection = None
    connections = None
    FieldSchema = None
    CollectionSchema = None
    DataType = None
    utility = None
import os
import json
from ..core.milvus_config import load_milvus_config


class MilvusClient:
    def __init__(
        self, host: str = None, port: int = None, collection_name: str = "kg_vectors"
    ):
        # Load settings from environment or fallback to defaults (including dim)
        from ..core.config import get_settings

        settings = get_settings()
        # Resolve host/port via config helper (allows JSON config file)
        self.host, self.port = (
            load_milvus_config()
            if host is None and port is None
            else (
                host or os.getenv("MILVUS_HOST", "localhost"),
                port or int(os.getenv("MILVUS_PORT", "19530")),
            )
        )
        self.collection_name = collection_name
        # Embedding dimension – read from config (default 768)
        self.dim = getattr(settings, "EMBEDDING_DIM", 768)
        # Determine if Milvus library is available
        self._fallback = False
        if any(v is None for v in (connections, utility, Collection)):
            # Use simple in‑memory dict as fallback store
            self._fallback = True
            self._store = {}
            return
        # Establish connection (idempotent)
        try:
            connections.connect("default", host=self.host, port=self.port)
        except Exception:
            self._fallback = True
            self._store = {}
            return
        # Ensure collection exists
        if not utility.has_collection(self.collection_name):
            self._create_collection()
        self.collection = Collection(self.collection_name)

    def _create_collection(self):
        # Simple schema: id (int64) primary, vector (float_vector) dim 768, metadata (JSON string)
        id_field = FieldSchema(
            name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
        )
        vector_field = FieldSchema(
            name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim
        )
        meta_field = FieldSchema(name="metadata", dtype=DataType.JSON)
        schema = CollectionSchema(
            fields=[id_field, vector_field, meta_field], description="KG vector store"
        )
        Collection(name=self.collection_name, schema=schema)

    def add_vector(self, vector: list[float], metadata: dict | None = None):
        """Insert a single vector with optional metadata.
        Returns the generated entity id (or a generated key in fallback).
        """
        metadata = metadata or {}
        if getattr(self, "_fallback", False):
            # Simple in‑memory storage; generate an incremental integer id
            key = len(self._store) + 1
            self._store[key] = {"vector": vector, "metadata": metadata}
            return key
        # Milvus expects list of vectors, list of metadata
        # Milvus schema has 3 fields (id auto‑generated, embedding, metadata). Only the non‑auto fields need values.
        entities = [
            [vector],  # embedding field (list of vectors)
            [metadata],  # metadata field (list of json objects)
        ]
        mr = self.collection.insert(entities)
        return mr.primary_keys[0]

    def search(self, query_vec: list[float], top_k: int = 5, expr: str = ""):
        """Perform ANN search.
        Returns list of (id, distance, metadata).
        """
        if getattr(self, "_fallback", False):
            # Naive linear search over in‑memory store
            results = []
            for key, entry in self._store.items():
                # Compute dot product similarity (simple approximation)
                vec = entry["vector"]
                # Ensure same length, pad zeros if needed
                min_len = min(len(vec), len(query_vec))
                sim = sum(v * query_vec[i] for i, v in enumerate(vec[:min_len]))
                results.append(
                    {"id": key, "distance": sim, "metadata": entry["metadata"]}
                )
            # Sort by distance descending (higher similarity first)
            results.sort(key=lambda x: x["distance"], reverse=True)
            return results[:top_k]
        # Milvus path
        search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_vec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["metadata"],
        )
        hits = []
        for hit in results[0]:
            hits.append(
                {
                    "id": hit.id,
                    "distance": hit.distance,
                    "metadata": hit.entity.get("metadata"),
                }
            )
        return hits
