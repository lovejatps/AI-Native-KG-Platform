from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get('/kg_integration_page?kg_id=123')
print('status', resp.status_code)
print('headers', resp.headers)
print('content bytes', len(resp.content))
print('content snippet', resp.content[:100])
