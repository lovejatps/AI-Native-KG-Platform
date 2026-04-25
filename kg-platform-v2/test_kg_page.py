from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.get('/kg_page')
print('Status', resp.status_code)
print('Contains fallback script?', 'Dayjs CDN 回退' in resp.text)
