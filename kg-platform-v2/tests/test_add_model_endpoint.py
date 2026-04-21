import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.models_store import create_model, get_model
from app.graph.neo4j_client import Neo4jClient

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def clear_models():
    # Clear fallback Neo4j in‑memory store before each test
    client = Neo4jClient()
    client._store.clear()
    client._relationships.clear()


@pytest.fixture(scope="function")
def kg_id():
    # Create a KG for testing
    resp = client.post("/kg/create", json={"name": "testkg", "description": "test"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_add_model_success(kg_id):
    # Test adding a model
    resp = client.post(f"/kg/{kg_id}/models", json={})
    assert resp.status_code == 200, resp.text
    # Note: This test might need to be updated based on actual response structure
    # For now, we assume it returns 200 for successful creation
