from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.get('/')
print('Status:', resp.status_code)
print('Semantic link present:', '<a href="/semantic_page">语义词典</a>' in resp.text)
