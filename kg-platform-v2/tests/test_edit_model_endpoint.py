import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.models_store import create_model, get_model

client = TestClient(app)


@pytest.fixture(scope="function")
def kg_id():
    # Create a KG for testing
    resp = client.post("/kg/create", json={"name": "testkg", "description": "test"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_edit_model_success(kg_id):
    # Create a dummy model directly via core store
    dummy_schema = {"entities": []}
    model = create_model(kg_id, dummy_schema)
    model_id = model["id"]
    # Prepare a valid updated schema
    updated_schema = {
        "entities": [{"name": "Person", "properties": []}],
        "relations": [],
    }
    resp = client.put(f"/kg/{kg_id}/models/{model_id}", json={"schema": updated_schema})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == model_id
    assert data["schema"] == updated_schema
    assert data["status"] == "草稿"


def test_edit_model_invalid_schema(kg_id):
    dummy_schema = {"entities": []}
    model = create_model(kg_id, dummy_schema)
    model_id = model["id"]
    # Missing required 'entities' key
    invalid_schema = {"foo": "bar"}
    resp = client.put(f"/kg/{kg_id}/models/{model_id}", json={"schema": invalid_schema})
    assert resp.status_code == 400
    assert "missing required key" in resp.json()["error"].lower()
