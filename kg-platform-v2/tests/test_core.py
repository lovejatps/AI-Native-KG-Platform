import os
import json
import pytest

from app.schema.schema_builder import build_schema
from app.rag.vector_store import VectorStore
from app.graph.graph_builder import upsert_graph


def test_schema_builder_versioning(tmp_path, monkeypatch):
    # Use temporary directory for schema versions
    from app.schema import schema_cache

    # Redirect version directory to tmp_path
    monkeypatch.setattr(schema_cache, "SCHEMA_DIR", tmp_path)
    # Ensure directory exists
    tmp_path.mkdir(parents=True, exist_ok=True)
    sample_text = "employee(id, name, company_id)"
    schema = build_schema(sample_text)
    assert "_version" in schema
    # Verify file persisted
    version = schema["_version"]
    persisted = schema_cache.load_schema(version)
    assert persisted == schema


def test_vector_store_add_and_search():
    store = VectorStore()
    vec = [0.1] * 768
    store.add_vector(key="test1", vector=vec, metadata={"entity_name": "TestEntity"})
    results = store.search(vec, top_k=5)
    # Should return at least one result containing our key
    keys = [r[0] for r in results]
    assert "test1" in keys


def test_graph_upsert_no_error():
    data = {
        "entities": [{"name": "Alice", "type": "Person"}],
        "relations": [{"from": "Alice", "to": "Acme Corp", "type": "WORKS_FOR"}],
    }
    try:
        upsert_graph(data)
    except Exception as e:
        pytest.fail(f"upsert_graph raised an exception: {e}")
