from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response, UploadFile


def user(username="alice"):
    return SimpleNamespace(username=username)


@pytest.mark.asyncio
async def test_home_page_serves_react_shell(main_module):
    response = await main_module.home(SimpleNamespace())

    assert response.status_code == 200
    assert 'id="root"' in response.body.decode()
    assert "/static/dist/assets/index.js" in response.body.decode()
    assert "/static/dist/assets/index.css" in response.body.decode()


@pytest.mark.asyncio
async def test_signup_sets_authenticated_session(main_module):
    response = Response()

    result = await main_module.auth_signup(
        SimpleNamespace(),
        response,
        main_module.AuthRequest(username="alice", password="password123"),
    )

    assert result.user["username"] == "alice"
    assert "studyspace_session=" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_auth_signin_rejects_invalid_credentials(main_module):
    response = Response()
    await main_module.auth_signup(
        SimpleNamespace(),
        Response(),
        main_module.AuthRequest(username="alice", password="password123"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await main_module.auth_signin(
            SimpleNamespace(),
            response,
            main_module.AuthRequest(username="alice", password="wrongpass"),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid username or password"


@pytest.mark.asyncio
async def test_chat_endpoint_with_selected_files_scoped_to_user(main_module):
    main_module.vector_store.get_document_metadata.side_effect = [
        {"filename": "file1.pdf", "owner_username": "alice"},
        {"filename": "file2.pdf", "owner_username": "alice"},
    ]
    main_module.rag_chat.chat.return_value = {
        "response": "Test response",
        "sources": [{"source": "test.pdf"}],
        "trace": {
            "generated_queries": [{"id": "q1", "text": "hello"}],
            "retrieval_runs": [],
            "fused_results": [],
        },
    }

    payload = main_module.ChatRequest(message="Hello", selected_files=["file1.pdf", "file2.pdf"])

    response = await main_module.chat(payload, current_user=user())

    assert response.response == "Test response"
    assert response.trace["generated_queries"][0]["id"] == "q1"
    main_module.rag_chat.chat.assert_called_once_with("Hello", "alice", ["file1.pdf", "file2.pdf"])


@pytest.mark.asyncio
async def test_documents_are_isolated_per_user(main_module):
    main_module.vector_store.list_documents.return_value = [{"filename": "alice.pdf", "tag": "Security"}]

    response = await main_module.list_documents(current_user=user())

    assert response == {"documents": [{"filename": "alice.pdf", "tag": "Security"}]}
    main_module.vector_store.list_documents.assert_called_once_with("alice")


@pytest.mark.asyncio
async def test_get_metadata_scoped_to_user(main_module):
    main_module.app.state.db.create_user("alice", "hash", "salt")
    main_module.app.state.db.create_user("bob", "hash", "salt")
    main_module.app.state.db.set_document_metadata("alice", "doc1.pdf", {"assessments": [{"item": "A1"}]})

    alice_response = await main_module.get_metadata(current_user=user("alice"))
    bob_response = await main_module.get_metadata(current_user=user("bob"))

    assert alice_response["doc1.pdf"]["assessments"][0]["item"] == "A1"
    assert bob_response == {}


@pytest.mark.asyncio
async def test_update_document_tag_endpoint(main_module):
    main_module.app.state.db.create_user("alice", "hash", "salt")
    main_module.vector_store.get_document_metadata.return_value = {
        "filename": "test.pdf",
        "owner_username": "alice",
    }
    main_module.vector_store.update_document_tag.return_value = True

    response = await main_module.update_document_tag(
        "test.pdf",
        main_module.DocumentTagRequest(tag=" NewTag "),
        current_user=user(),
    )

    assert response == {"message": "Document tag updated successfully", "tag": "NewTag"}
    assert "NewTag" in main_module.app.state.db.get_tags("alice")
    main_module.vector_store.update_document_tag.assert_called_once_with("alice", "test.pdf", "NewTag")


@pytest.mark.asyncio
async def test_update_document_tag_nonexistent_fails(main_module):
    main_module.vector_store.get_document_metadata.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await main_module.update_document_tag(
            "missing.pdf",
            main_module.DocumentTagRequest(tag="Any"),
            current_user=user(),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_removes_files_and_metadata(main_module, tmp_path):
    main_module.app.state.db.create_user("alice", "hash", "salt")
    uploaded_file = tmp_path / "source.pdf"
    processed_file = tmp_path / "source.pdf.md"
    uploaded_file.write_text("source", encoding="utf-8")
    processed_file.write_text("processed", encoding="utf-8")

    main_module.vector_store.get_document_metadata.return_value = {
        "filename": "source.pdf",
        "owner_username": "alice",
        "processed_path": str(processed_file),
    }
    main_module.vector_store.get_document_paths.return_value = [str(uploaded_file)]
    main_module.vector_store.delete_document.return_value = True
    main_module.app.state.db.set_document_metadata("alice", "source.pdf", {"assessments": []})

    response = await main_module.delete_document("source.pdf", current_user=user())

    assert response == {"message": "Document 'source.pdf' deleted successfully"}
    assert not uploaded_file.exists()
    assert not processed_file.exists()
    assert main_module.app.state.db.get_all_metadata("alice") == {}


@pytest.mark.asyncio
async def test_generate_quiz_returns_404_when_processed_file_missing(main_module):
    main_module.vector_store.get_document_metadata.return_value = {
        "filename": "quiz.pdf",
        "owner_username": "alice",
        "processed_path": "/tmp/quiz.pdf.md",
    }
    main_module.quiz_generator.generate_quiz.side_effect = FileNotFoundError

    with pytest.raises(HTTPException) as exc_info:
        await main_module.generate_quiz(
            main_module.QuizRequest(filename="quiz.pdf", num_questions=3),
            current_user=user(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Document not found or not processed yet"


@pytest.mark.asyncio
async def test_generate_flashcards_returns_payload(main_module):
    main_module.vector_store.get_document_metadata.return_value = {
        "filename": "cards.pdf",
        "owner_username": "alice",
        "processed_path": "/tmp/cards.pdf.md",
    }
    main_module.flashcard_generator.generate_flashcards.return_value = {
        "title": "Flashcards",
        "cards": [{"id": 1, "front": "Q", "back": "A"}],
    }

    response = await main_module.generate_flashcards(
        main_module.FlashcardRequest(filename="cards.pdf", num_cards=4),
        current_user=user(),
    )

    assert response["title"] == "Flashcards"


@pytest.mark.asyncio
async def test_upload_document_rejects_invalid_filename(main_module):
    upload = UploadFile(filename="", file=BytesIO(b"content"))

    with pytest.raises(HTTPException) as exc_info:
        await main_module.upload_document(upload, current_user=user())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid filename"
