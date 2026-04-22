import os
from fastapi.testclient import TestClient

# Enable debug logs
os.environ['LOG_LEVEL'] = 'DEBUG'

from app.main import app

client = TestClient(app)

session_id = 'e2e-test-session'

# First message
resp1 = client.post('/chat', json={'session_id': session_id, 'message': 'Hello'})
print('First response:', resp1.json())

# Second message – should include prior context
resp2 = client.post('/chat', json={'session_id': session_id, 'message': 'What can you do?'})
print('Second response:', resp2.json())
