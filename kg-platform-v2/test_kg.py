from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.get('/kg')
print('GET /kg status', resp.status_code)
print('Redirect location header', resp.headers.get('location'))
resp2 = client.get('/kg_page')
print('GET /kg_page status', resp2.status_code)
print('Content size', len(resp2.content))
