from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/kg_integration_page?kg_id=123')
print('status', resp.status_code)
print('content_type', resp.headers.get('content-type'))
print('snippet', resp.text[:200])
