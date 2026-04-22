"""Tests for the new /chat endpoint with context management.

The real LLM call is mocked to avoid external network dependency.
"""

import json
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)

def test_chat_endpoint_basic():
    session_id = "test-session-123"
    user_msg = "Hello"
    # Mock the LLM chat method to return a fixed response
    with patch("app.core.llm.llm.chat_vllm_direct", return_value="Mocked reply") as mock_llm:
        response = client.post(
            "/chat",
            json={"session_id": session_id, "message": user_msg},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Mocked reply"
        # Ensure the LLM was called with a context that includes the user message
        mock_llm.assert_called_once()
        args, _ = mock_llm.call_args
        # The context should be a list with a single user message dict
        assert isinstance(args[0], list)
        assert args[0] == [{"role": "user", "content": user_msg}]

def test_chat_context_persistence():
    session_id = "persist-session"
    # First message
    with patch("app.core.llm.llm.chat_vllm_direct", return_value="First reply"):
        client.post("/chat", json={"session_id": session_id, "message": "Hi"})
    # Second message – mock should receive both prior messages in context
    with patch("app.core.llm.llm.chat_vllm_direct", return_value="Second reply") as mock_llm:
        client.post("/chat", json={"session_id": session_id, "message": "How are you?"})
        mock_llm.assert_called_once()
        args, _ = mock_llm.call_args
        # Context should include the previous user and assistant messages plus new user
        assert len(args[0]) == 3
        assert args[0][0]["role"] == "user"
        assert args[0][0]["content"] == "Hi"
        assert args[0][1]["role"] == "assistant"
        assert args[0][1]["content"] == "First reply"
        assert args[0][2]["role"] == "user"
        assert args[0][2]["content"] == "How are you?"
