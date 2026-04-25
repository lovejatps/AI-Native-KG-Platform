import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_field_crud():
    # list (should be empty or have init data)
    r = client.get('/semantic/fields', params={'limit':10, 'offset':0})
    assert r.status_code == 200
    data = r.json()
    print('list fields', data)
    # create
    payload = {
        "library_name": "testLib",
        "table_name": "TestTable",
        "column_name": "test_col",
        "synonyms": ["别名1", "别名2"],
        "description": "测试字段"
    }
    r = client.post('/semantic/fields', json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    field_id = created['id']
    # duplicate should fail
    r = client.post('/semantic/fields', json=payload)
    assert r.status_code == 400
    # update
    update_payload = payload.copy()
    update_payload['description'] = '更新描述'
    r = client.put(f'/semantic/fields/{field_id}', json=update_payload)
    assert r.status_code == 200
    # delete
    r = client.delete(f'/semantic/fields/{field_id}')
    assert r.status_code == 204

if __name__ == '__main__':
    test_field_crud()
    print('All semantic API tests passed')
