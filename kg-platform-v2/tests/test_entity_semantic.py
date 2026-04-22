import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_entity_semantic_not_found():
    """请求不存在的实体语义名称应返回 404"""
    resp = client.get("/entity/does_not_exist/semantic")
    assert resp.status_code == 404
    json_body = resp.json()
    assert "detail" in json_body
    assert "not found" in json_body["detail"].lower()

def test_put_entity_semantic_not_found():
    """更新不存在实体的语义名称应返回 404 或 400"""
    resp = client.put(
        "/entity/does_not_exist/semantic",
        json={"semanticName": "新名称"},
    )
    # Depending on implementation, may be 404 (entity not found) or 400 (semanticName missing?)
    assert resp.status_code in (404, 400)
