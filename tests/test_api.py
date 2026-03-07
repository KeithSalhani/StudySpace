import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["GEMINI_API_KEY"] = "test_key"

import app.main as main_module
from app.db.metadata import JSONDatabase


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = JSONDatabase(str(tmp_path / "test_db.json"))
    monkeypatch.setattr(main_module, "db", test_db)
    monkeypatch.setattr(main_module.app.state, "db", test_db)
    monkeypatch.setattr(main_module.upload_jobs, "database", test_db)
    with TestClient(main_module.app) as test_client:
        yield test_client


def sign_up(client: TestClient, username: str = "alice", password: str = "password123"):
    return client.post("/auth/signup", json={"username": username, "password": password})


def test_home_page_serves_react_shell(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="root"' in response.text
    assert '/static/dist/assets/index.js' in response.text
    assert '/static/dist/assets/index.css' in response.text


def test_signup_sets_authenticated_session(client):
    response = sign_up(client)

    assert response.status_code == 201
    assert response.json()["user"]["username"] == "alice"
    assert main_module.SESSION_COOKIE_NAME in response.cookies


def test_auth_me_requires_cookie(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/documents")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


@patch("app.main.rag_chat")
@patch("app.main.vector_store")
def test_chat_endpoint_with_selected_files_scoped_to_user(mock_vector_store, mock_rag_chat, client):
    sign_up(client)
    mock_vector_store.get_document_metadata.side_effect = [
        {"filename": "file1.pdf", "owner_username": "alice"},
        {"filename": "file2.pdf", "owner_username": "alice"},
    ]
    mock_rag_chat.chat.return_value = ("Test response", [{"source": "test.pdf"}])

    payload = {
        "message": "Hello",
        "selected_files": ["file1.pdf", "file2.pdf"]
    }
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    assert response.json()["response"] == "Test response"
    mock_rag_chat.chat.assert_called_once_with("Hello", "alice", ["file1.pdf", "file2.pdf"])


def test_notes_are_isolated_per_user(client):
    sign_up(client, "alice", "password123")
    response = client.post("/notes", json={"content": "Alice note"})
    assert response.status_code == 200

    client.post("/auth/logout")
    sign_up(client, "bob", "password123")

    notes_response = client.get("/notes")
    assert notes_response.status_code == 200
    assert notes_response.json()["notes"] == []


@patch("app.main.vector_store")
def test_documents_are_isolated_per_user(mock_vector_store, client):
    sign_up(client, "alice", "password123")
    mock_vector_store.list_documents.return_value = [{"filename": "alice.pdf", "tag": "Security"}]
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json()["documents"] == [{"filename": "alice.pdf", "tag": "Security"}]
    mock_vector_store.list_documents.assert_called_once_with("alice")
