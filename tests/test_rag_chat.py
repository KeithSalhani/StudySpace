import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.rag import RAGChat


@pytest.fixture
def mock_vector_store():
    return MagicMock()


@pytest.fixture
def mock_genai():
    with patch("app.core.rag.genai") as mock:
        yield mock


@pytest.fixture
def rag_chat(mock_vector_store, mock_genai):
    return RAGChat(mock_vector_store, api_key="test_key")


def make_response(text):
    response = MagicMock()
    response.text = text
    return response


def test_chat_success_returns_trace_and_sources(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {"text": "distributed systems summary", "goal": "overview", "module_tag": None},
                        {"text": "distributed systems consistency models", "goal": "concepts", "module_tag": None},
                        {"text": "distributed systems examples", "goal": "examples", "module_tag": None},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "needs_full_documents": False,
                    "full_document_filenames": []
                }
            )
        ),
        make_response("AI Response [S1]"),
    ]

    mock_vector_store.list_documents.return_value = [
        {"filename": "week1.pdf", "tag": "Uncategorized"},
        {"filename": "week2.pdf", "tag": "Uncategorized"},
    ]
    mock_vector_store.search.side_effect = [
        [
            {
                "id": "doc1_chunk_0",
                "document": "Consistency keeps replicas aligned.",
                "metadata": {"doc_id": "doc1", "filename": "week1.pdf", "chunk_index": 0, "tag": ""},
                "distance": 0.12,
            }
        ],
        [
            {
                "id": "doc2_chunk_0",
                "document": "CAP theorem explains trade-offs.",
                "metadata": {"doc_id": "doc2", "filename": "week2.pdf", "chunk_index": 0, "tag": ""},
                "distance": 0.19,
            }
        ],
        [],
    ]

    payload = rag_chat.chat("Explain distributed systems", owner_username="alice")

    assert payload["response"] == "AI Response [S1]"
    assert len(payload["trace"]["generated_queries"]) == 3
    assert len(payload["trace"]["retrieval_runs"]) == 3
    assert payload["trace"]["summary"]["passages_used"] == 2
    assert payload["sources"][0]["filename"] == "week1.pdf"
    assert mock_client.models.generate_content.call_count == 3
    assert mock_vector_store.search.call_count == 3


def test_chat_uses_module_tag_filter_when_plan_selects_one(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {"text": "memory forensics process list", "goal": "facts", "module_tag": "Forensics"},
                        {"text": "memory forensics artifacts", "goal": "artifacts", "module_tag": "Forensics"},
                        {"text": "memory forensics examples", "goal": "examples", "module_tag": "Forensics"},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "needs_full_documents": False,
                    "full_document_filenames": []
                }
            )
        ),
        make_response("Answer"),
    ]
    mock_vector_store.list_documents.return_value = [
        {"filename": "lab1.pdf", "tag": "Forensics"},
        {"filename": "lab2.pdf", "tag": "Security"},
    ]
    mock_vector_store.search.side_effect = [[], [], []]

    rag_chat.chat("How do I inspect a memory image?", owner_username="alice")

    for call in mock_vector_store.search.call_args_list:
        assert call.kwargs["selected_tags"] == ["Forensics"]


def test_chat_with_selected_files_does_not_add_tag_filter(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {"text": "file1 summary", "goal": "overview", "module_tag": "Security"},
                        {"text": "file1 definitions", "goal": "definitions", "module_tag": "Security"},
                        {"text": "file1 examples", "goal": "examples", "module_tag": "Security"},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "needs_full_documents": False,
                    "full_document_filenames": []
                }
            )
        ),
        make_response("Answer"),
    ]
    mock_vector_store.list_documents.return_value = [{"filename": "file1.pdf", "tag": "Security"}]
    mock_vector_store.search.side_effect = [[], [], []]

    rag_chat.chat("Summarize this file", owner_username="alice", selected_files=["file1.pdf"])

    for call in mock_vector_store.search.call_args_list:
        assert call.kwargs["selected_files"] == ["file1.pdf"]
        assert call.kwargs["selected_tags"] is None


def test_chat_empty_response_raises(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {"text": "query one", "goal": "one", "module_tag": None},
                        {"text": "query two", "goal": "two", "module_tag": None},
                        {"text": "query three", "goal": "three", "module_tag": None},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "needs_full_documents": False,
                    "full_document_filenames": []
                }
            )
        ),
        make_response(""),
    ]
    mock_vector_store.list_documents.return_value = []
    mock_vector_store.search.side_effect = [[], [], []]

    with pytest.raises(ValueError, match="Empty response"):
        rag_chat.chat("Hello", owner_username="alice")


def test_create_prompt_with_context(rag_chat):
    prompt = rag_chat._create_prompt(
        "Question?",
        [
            {
                "source_id": "S1",
                "filename": "week1.pdf",
                "chunk_index": 0,
                "tag": "Security",
                "content": "Relevant info.",
            }
        ],
    )

    assert "Question?" in prompt
    assert "Relevant info." in prompt
    assert "[S1 | week1.pdf | chunk 0 | module Security]" in prompt


def test_create_prompt_no_context(rag_chat):
    prompt = rag_chat._create_prompt("Question?", [])

    assert "Question?" in prompt
    assert "No relevant evidence was retrieved" in prompt
