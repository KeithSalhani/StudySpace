import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Set API key for testing before importing app
import os
os.environ["GEMINI_API_KEY"] = "test_key"

from app.main import app

client = TestClient(app)

def test_home_page_serves_react_shell():
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="root"' in response.text
    assert '/static/dist/assets/index.js' in response.text
    assert '/static/dist/assets/index.css' in response.text

@patch("app.main.rag_chat")
def test_chat_endpoint_with_selected_files(mock_rag_chat):
    # Setup mock
    mock_rag_chat.chat.return_value = ("Test response", [{"source": "test.pdf"}])
    
    # Execute request
    payload = {
        "message": "Hello",
        "selected_files": ["file1.pdf", "file2.pdf"]
    }
    response = client.post("/chat", json=payload)
    
    # Verify response
    assert response.status_code == 200
    assert response.json()["response"] == "Test response"
    
    # Verify the endpoint passed selected_files to the rag_chat
    mock_rag_chat.chat.assert_called_once_with("Hello", ["file1.pdf", "file2.pdf"])

@patch("app.main.rag_chat")
def test_chat_endpoint_without_selected_files(mock_rag_chat):
    # Setup mock
    mock_rag_chat.chat.return_value = ("Test response", [{"source": "test.pdf"}])
    
    # Execute request
    payload = {
        "message": "Hello"
    }
    response = client.post("/chat", json=payload)
    
    # Verify response
    assert response.status_code == 200
    
    # Verify the endpoint defaults to None or doesn't pass it
    mock_rag_chat.chat.assert_called_once_with("Hello", None)

@patch("app.main.rag_chat")
def test_homepage_smoke_test(mock_rag_chat):
    """Tests the root endpoint '/' to ensure basic API routing is up, 
    even if frontend assets are missing."""
    
    # We don't expect rag_chat to be called for a simple homepage check
    response = client.get("/")
    
    # Expecting 200 OK for the API endpoint, or perhaps a redirect if it's configured that way.
    # Since it's a *smoke test* for the API, we assume a successful response code.
    assert response.status_code in [200, 307, 302] # 200 OK, or Redirect if it redirects to docs/index.html
    
    # Ensure rag_chat was not invoked by this simple GET request
    mock_rag_chat.chat.assert_not_called()
