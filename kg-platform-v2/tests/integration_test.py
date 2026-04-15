# Integration tests for full KG pipeline
# Prerequisites: docker-compose with Neo4j, Milvus, Redis running.
# FastAPI TestClient will start the app in-process.

import os
import tempfile
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.graph.neo4j_client import Neo4jClient
from app.rag.vector_store import VectorStore
from app.core.incremental import _hash_text

client = TestClient(app)
neo = Neo4jClient()
store = VectorStore()


def _cleanup():
    # Delete all Entity nodes
    neo.run("MATCH (n:Entity) DETACH DELETE n")
    # Clear Milvus collection if possible (fallback store)
    if hasattr(store.client, "collection") and store.client.collection:
        store.client.collection.delete()


@pytest.fixture(autouse=True)
def clean():
    _cleanup()
    yield
    _cleanup()


def test_ingest_and_query():
    # Create temporary txt file (loader fallback will return placeholder text)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write("张三在A公司担任工程师。".encode("utf-8"))
        tmp_path = tmp.name

    # Call ingestion endpoint
    resp = client.post("/document/ingest", json={"file_path": tmp_path})
    assert resp.status_code == 200
    assert resp.json().get("status") == "processed"

    # Give a short pause for async steps (if any)
    time.sleep(1)

    # Verify Neo4j node exists and full‑text index works
    result = neo.run("MATCH (e:Entity {name: $name}) RETURN e", {"name": "张三"})
    nodes = list(result)
    assert len(nodes) == 1
    assert nodes[0]["e"].get("name") == "张三"

    # Full‑text search should return the same entity
    ft_hits = neo.fulltext_search("张三")
    assert any(hit["properties"].get("name") == "张三" for hit in ft_hits), (
        "Full‑text index did not return the inserted node"
    )

    # Verify vector stored (search with zero vector fallback)
    hits = store.search([0.0] * store.client.dim, top_k=5)
    chunk_hash = _hash_text("张三在A公司担任工程师。")
    found = any(meta.get("key") == f"chunk:{chunk_hash}" for _, _, meta in hits)
    assert found, "Vector for processed chunk should be present"

    # Clean up temporary file
    os.unlink(tmp_path)
