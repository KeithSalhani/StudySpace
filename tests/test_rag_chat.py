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
                        {"text": "distributed systems summary", "goal": "overview", "search_mode": "unfocused", "module_tag": None, "target_files": []},
                        {"text": "distributed systems consistency models", "goal": "concepts", "search_mode": "unfocused", "module_tag": None, "target_files": []},
                        {"text": "distributed systems examples", "goal": "examples", "search_mode": "unfocused", "module_tag": None, "target_files": []},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "answer": "",
                    "needs_full_documents": False,
                    "full_document_filenames": [],
                    "missing_information": "",
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
    assert payload["trace"]["generated_queries"][0]["search_mode"] == "unfocused"
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
                        {"text": "memory forensics process list", "goal": "facts", "search_mode": "focused", "module_tag": "Forensics", "target_files": []},
                        {"text": "memory forensics artifacts", "goal": "artifacts", "search_mode": "focused", "module_tag": "Forensics", "target_files": []},
                        {"text": "memory forensics examples", "goal": "examples", "search_mode": "focused", "module_tag": "Forensics", "target_files": []},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "answer": "",
                    "needs_full_documents": False,
                    "full_document_filenames": [],
                    "missing_information": "",
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


def test_chat_with_selected_files_can_add_exact_file_and_tag_focus(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {
                            "text": "file1 summary",
                            "goal": "overview",
                            "search_mode": "focused",
                            "module_tag": "Security",
                            "target_files": ["file1.pdf"],
                        }
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "answer": "Answer",
                    "needs_full_documents": False,
                    "full_document_filenames": [],
                    "missing_information": "",
                }
            )
        ),
    ]
    mock_vector_store.list_documents.return_value = [{"filename": "file1.pdf", "tag": "Security"}]
    mock_vector_store.search.side_effect = [[]]

    rag_chat.chat("Summarize this file", owner_username="alice", selected_files=["file1.pdf"])

    mock_vector_store.search.assert_called_once()
    assert mock_vector_store.search.call_args.kwargs["selected_files"] == ["file1.pdf"]
    assert mock_vector_store.search.call_args.kwargs["selected_tags"] == ["Security"]


def test_chat_full_document_plan_reads_exact_files_directly(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {
                            "text": "Compare the named exam papers directly",
                            "goal": "Read the requested papers in full.",
                            "search_mode": "full_document",
                            "module_tag": "Exam Papers",
                            "target_files": ["18-19.pdf", "22-23.pdf"],
                        }
                    ]
                }
            )
        ),
        make_response("Direct full-document answer [F1] [F2]"),
    ]
    mock_vector_store.list_documents.return_value = [
        {"filename": "18-19.pdf", "tag": "Exam Papers"},
        {"filename": "22-23.pdf", "tag": "Exam Papers"},
    ]
    mock_vector_store.get_full_document_content.side_effect = [
        {"filename": "18-19.pdf", "tag": "Exam Papers", "content": "Paper 18-19 full text", "source": "processed_markdown"},
        {"filename": "22-23.pdf", "tag": "Exam Papers", "content": "Paper 22-23 full text", "source": "processed_markdown"},
        {"filename": "18-19.pdf", "tag": "Exam Papers", "content": "Paper 18-19 full text", "source": "processed_markdown"},
        {"filename": "22-23.pdf", "tag": "Exam Papers", "content": "Paper 22-23 full text", "source": "processed_markdown"},
    ]

    payload = rag_chat.chat("Compare 18-19.pdf and 22-23.pdf", owner_username="alice")

    assert payload["response"] == "Direct full-document answer [F1] [F2]"
    assert payload["trace"]["generated_queries"] == [
        {
            "id": "q1",
            "text": "Compare the named exam papers directly",
            "goal": "Read the requested papers in full.",
            "search_mode": "full_document",
            "module_tag": "Exam Papers",
            "target_files": ["18-19.pdf", "22-23.pdf"],
            "results_found": 0,
        }
    ]
    assert payload["trace"]["full_document_fetches"] == [
        {
            "source_id": "F1",
            "filename": "18-19.pdf",
            "tag": "Exam Papers",
            "source": "processed_markdown",
            "reason": "Read the requested papers in full.",
            "query_id": "q1",
            "search_mode": "full_document",
        },
        {
            "source_id": "F2",
            "filename": "22-23.pdf",
            "tag": "Exam Papers",
            "source": "processed_markdown",
            "reason": "Read the requested papers in full.",
            "query_id": "q1",
            "search_mode": "full_document",
        },
    ]
    assert payload["sources"] == [
        {
            "source_id": "F1",
            "doc_id": None,
            "filename": "18-19.pdf",
            "chunk_index": None,
            "distance": None,
            "tag": "Exam Papers",
            "source_type": "full_document",
        },
        {
            "source_id": "F2",
            "doc_id": None,
            "filename": "22-23.pdf",
            "chunk_index": None,
            "distance": None,
            "tag": "Exam Papers",
            "source_type": "full_document",
        },
    ]
    assert mock_vector_store.search.call_count == 0
    assert mock_client.models.generate_content.call_count == 2


def test_chat_empty_response_raises(rag_chat, mock_vector_store, mock_genai):
    mock_client = mock_genai.Client.return_value
    mock_client.models.generate_content.side_effect = [
        make_response(
            json.dumps(
                {
                    "queries": [
                        {"text": "query one", "goal": "one", "search_mode": "unfocused", "module_tag": None, "target_files": []},
                        {"text": "query two", "goal": "two", "search_mode": "unfocused", "module_tag": None, "target_files": []},
                        {"text": "query three", "goal": "three", "search_mode": "unfocused", "module_tag": None, "target_files": []},
                    ]
                }
            )
        ),
        make_response(
            json.dumps(
                {
                    "answer": "",
                    "needs_full_documents": False,
                    "full_document_filenames": [],
                    "missing_information": "",
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


def test_normalize_query_plan_deduplicates_and_backfills_from_fallback(rag_chat):
    normalized = rag_chat._normalize_query_plan(
        [
            {"text": "  Security basics  ", "goal": "overview", "search_mode": "focused", "module_tag": "Security", "target_files": []},
            {"text": "security basics", "goal": "duplicate", "search_mode": "focused", "module_tag": "Security", "target_files": []},
        ],
        {"tags": {"Security": ["week1.pdf"]}},
        "Explain security basics",
    )

    assert len(normalized) == 1
    assert normalized[0]["text"] == "Security basics"
    assert normalized[0]["search_mode"] == "focused"
    assert normalized[0]["module_tag"] == "Security"
    assert normalized[0]["target_files"] == []


def test_normalize_query_plan_filters_unknown_file_targets(rag_chat):
    normalized = rag_chat._normalize_query_plan(
        [
            {
                "text": "Compare files directly",
                "goal": "Review named files",
                "search_mode": "full_document",
                "module_tag": "Exam Papers",
                "target_files": ["18-19.pdf", "missing.pdf"],
            }
        ],
        {"tags": {"Exam Papers": ["18-19.pdf", "22-23.pdf"]}},
        "Compare exam papers",
    )

    assert normalized == [
        {
            "query_id": "q1",
            "text": "Compare files directly",
            "goal": "Review named files",
            "search_mode": "full_document",
            "module_tag": "Exam Papers",
            "target_files": ["18-19.pdf"],
        }
    ]


def test_normalize_answer_plan_filters_unknown_and_duplicate_filenames(rag_chat):
    payload = rag_chat._normalize_answer_plan(
        {
            "answer": "Draft answer",
            "needs_full_documents": True,
            "full_document_filenames": ["week1.pdf", "WEEK1.PDF", "missing.pdf", "week2.pdf"],
            "missing_information": "Need exact examples",
        },
        ["week1.pdf", "week2.pdf"],
    )

    assert payload == {
        "answer": "Draft answer",
        "needs_full_documents": True,
        "full_document_filenames": ["week1.pdf", "week2.pdf"],
        "missing_information": "Need exact examples",
    }


def test_generate_response_with_document_fallback_returns_direct_answer_without_model_call(
    rag_chat, mock_vector_store
):
    rag_chat._assess_retrieved_evidence = MagicMock(
        return_value={
            "answer": "Use the retrieved chunks.",
            "needs_full_documents": False,
            "full_document_filenames": [],
            "missing_information": "",
        }
    )

    payload = rag_chat._generate_response_with_document_fallback(
        message="Question",
        owner_username="alice",
        fused_results=[],
    )

    assert payload == {
        "response": "Use the retrieved chunks.",
        "full_document_sources": [],
        "full_document_fetches": [],
    }
    mock_vector_store.get_full_document_content.assert_not_called()


def test_generate_response_with_document_fallback_uses_full_documents(rag_chat, mock_vector_store, mock_genai):
    rag_chat._assess_retrieved_evidence = MagicMock(
        return_value={
            "answer": "",
            "needs_full_documents": True,
            "full_document_filenames": ["week1.pdf"],
            "missing_information": "Need the full explanation",
        }
    )
    mock_vector_store.get_full_document_content.return_value = {
        "filename": "week1.pdf",
        "tag": "Security",
        "content": "Full document content",
        "source": "processed_markdown",
    }
    mock_genai.Client.return_value.models.generate_content.return_value = make_response("Expanded answer [F1]")

    payload = rag_chat._generate_response_with_document_fallback(
        message="Question",
        owner_username="alice",
        fused_results=[
            {
                "source_id": "S1",
                "filename": "week1.pdf",
                "chunk_index": 0,
                "tag": "Security",
                "content": "Chunk content",
            }
        ],
    )

    assert payload["response"] == "Expanded answer [F1]"
    assert payload["full_document_sources"] == [
        {
            "source_id": "F1",
            "doc_id": None,
            "filename": "week1.pdf",
            "chunk_index": None,
            "distance": None,
            "tag": "Security",
            "source_type": "full_document",
        }
    ]
    assert payload["full_document_fetches"] == [
        {
            "source_id": "F1",
            "filename": "week1.pdf",
            "tag": "Security",
            "source": "processed_markdown",
            "reason": "Need the full explanation",
            "query_id": "fallback",
            "search_mode": "fallback_full_document",
        }
    ]


def test_make_snippet_truncates_long_text(rag_chat):
    snippet = rag_chat._make_snippet("word " * 100, limit=25)

    assert len(snippet) <= 25
    assert snippet.endswith("…")
