import pytest
from fastapi.testclient import TestClient
from app.main import app  # 假设入口在 app/main.py

client = TestClient(app)


def test_entity_not_found_404():
    """请求不存在的实体应返回 404"""
    resp = client.get("/entity/this_entity_does_not_exist_123")
    assert resp.status_code == 404
    json_body = resp.json()
    assert "detail" in json_body
    assert "not found" in json_body["detail"].lower()
