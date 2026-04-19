import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.topic_miner import TopicMiner


@pytest.fixture
def mock_genai():
    with patch("app.core.topic_miner.genai") as mock:
        yield mock


@pytest.fixture
def mock_types():
    with patch("app.core.topic_miner.types") as mock:
        yield mock


@pytest.fixture
def document_processor():
    return MagicMock()


@pytest.fixture
def topic_miner(document_processor, mock_genai):
    return TopicMiner(document_processor, api_key="test_key")


def test_init_requires_api_key(monkeypatch, document_processor):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError):
        TopicMiner(document_processor)


def test_analyze_folder_runs_progress_and_falls_back_when_synthesis_fails(topic_miner):
    documents = [
        {"id": "1", "filename": "paper1.pdf", "path": "/tmp/paper1.pdf"},
        {"id": "2", "filename": "paper2.pdf", "path": "/tmp/paper2.pdf"},
    ]
    extracted = [
        {
            "document_id": "1",
            "filename": "paper1.pdf",
            "questions": [
                {
                    "question_number": 1,
                    "topic": "Authentication",
                    "subtopic": "Passwords",
                    "question_summary": "Explain password storage",
                }
            ],
        },
        {
            "document_id": "2",
            "filename": "paper2.pdf",
            "questions": [
                {
                    "question_number": 2,
                    "topic": "Authentication",
                    "subtopic": "MFA",
                    "question_summary": "Discuss multi-factor auth",
                }
            ],
        },
    ]
    progress_updates = []

    with patch.object(topic_miner, "_extract_paper_topics", side_effect=extracted), patch.object(
        topic_miner, "_synthesize_folder_topics", side_effect=RuntimeError("Gemini unavailable")
    ):
        result = topic_miner.analyze_folder(
            "Security",
            documents,
            progress_callback=lambda stage, progress: progress_updates.append((stage, progress)),
        )

    assert result["paper_count"] == 2
    assert result["analyzed_paper_count"] == 2
    assert result["summary"]["theme_count"] == 1
    assert result["themes"][0]["canonical_topic"] == "Authentication"
    assert result["themes"][0]["frequency"] == {"papers_with_topic": 2, "total_papers": 2}
    assert progress_updates[-1] == ("Topic mining complete", 100)


def test_analyze_folder_handles_per_paper_extraction_failure_and_requires_one_success(topic_miner):
    documents = [
        {"id": "1", "filename": "paper1.pdf", "path": "/tmp/paper1.pdf"},
        {"id": "2", "filename": "paper2.pdf", "path": "/tmp/paper2.pdf"},
    ]
    success_payload = {
        "document_id": "2",
        "filename": "paper2.pdf",
        "questions": [
            {
                "question_number": 1,
                "topic": "Networks",
                "subtopic": "Routing",
                "question_summary": "Compare routing protocols",
            }
        ],
    }

    with patch.object(
        topic_miner,
        "_extract_paper_topics",
        side_effect=[ValueError("broken pdf"), success_payload],
    ), patch.object(
        topic_miner,
        "_synthesize_folder_topics",
        return_value={"themes": [], "observations": ["Use past papers"]},
    ):
        result = topic_miner.analyze_folder("Networks", documents)

    assert result["papers"][0]["error"] == "broken pdf"
    assert result["papers"][1]["questions"][0]["topic"] == "Networks"
    assert result["observations"] == ["Use past papers"]

    with patch.object(topic_miner, "_extract_paper_topics", side_effect=RuntimeError("failed")):
        with pytest.raises(ValueError, match="Could not extract topics"):
            topic_miner.analyze_folder("Networks", documents)


def test_analyze_folder_rejects_empty_document_list(topic_miner):
    with pytest.raises(ValueError, match="No exam papers found"):
        topic_miner.analyze_folder("Security", [])


def test_load_document_content_uses_processor_for_pdf_and_text_file(tmp_path, topic_miner, document_processor):
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("placeholder", encoding="utf-8")
    document_processor.process_document.return_value = "  extracted pdf text  "

    content = topic_miner._load_document_content({"filename": "paper.pdf", "path": str(pdf_path)})

    assert content == "extracted pdf text"
    document_processor.process_document.assert_called_once_with(str(pdf_path))

    text_path = tmp_path / "paper.txt"
    text_path.write_text("  plain text content  ", encoding="utf-8")
    assert topic_miner._load_document_content({"filename": "paper.txt", "path": str(text_path)}) == "plain text content"

    with pytest.raises(FileNotFoundError):
        topic_miner._load_document_content({"filename": "missing.txt", "path": str(tmp_path / 'missing.txt')})

    empty_path = tmp_path / "empty.txt"
    empty_path.write_text("   ", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        topic_miner._load_document_content({"filename": "empty.txt", "path": str(empty_path)})


def test_build_paper_contents_handles_inline_pdf_uploaded_pdf_and_plain_text(tmp_path, topic_miner, mock_types):
    inline_pdf = tmp_path / "inline.pdf"
    inline_pdf.write_bytes(b"%PDF-inline")
    mock_types.Part.from_bytes.return_value = "inline-part"

    contents, uploaded_name = topic_miner._build_paper_contents(
        {"filename": "inline.pdf", "path": str(inline_pdf)},
        "prompt",
    )

    assert contents == ["prompt", "inline-part"]
    assert uploaded_name is None
    mock_types.Part.from_bytes.assert_called_once()

    large_pdf = tmp_path / "large.pdf"
    large_pdf.write_bytes(b"x" * (TopicMiner.INLINE_PDF_LIMIT_BYTES + 1))
    uploaded_file = MagicMock()
    uploaded_file.name = "gemini-file-1"
    topic_miner.client.files.upload.return_value = uploaded_file

    contents, uploaded_name = topic_miner._build_paper_contents(
        {"filename": "large.pdf", "path": str(large_pdf)},
        "prompt",
    )

    assert contents == ["prompt", uploaded_file]
    assert uploaded_name == "gemini-file-1"

    text_file = tmp_path / "paper.txt"
    text_file.write_text("plain text fallback", encoding="utf-8")
    contents, uploaded_name = topic_miner._build_paper_contents(
        {"filename": "paper.txt", "path": str(text_file)},
        "prompt",
    )
    assert uploaded_name is None
    assert "Plain text fallback for a non-PDF exam document" in contents[0]
    assert "plain text fallback" in contents[0]


def test_generate_json_parses_fenced_json_and_deletes_uploaded_file(topic_miner):
    response = MagicMock()
    response.text = '```json\n{"themes": []}\n```'
    topic_miner.client.models.generate_content.return_value = response

    payload = topic_miner._generate_json("prompt", uploaded_file_name="gemini-file-1")

    assert payload == {"themes": []}
    topic_miner.client.files.delete.assert_called_once_with(name="gemini-file-1")


def test_generate_json_rejects_empty_or_non_object_payload(topic_miner):
    empty_response = MagicMock()
    empty_response.text = ""
    topic_miner.client.models.generate_content.return_value = empty_response
    with pytest.raises(ValueError, match="Empty response"):
        topic_miner._generate_json("prompt")

    list_response = MagicMock()
    list_response.text = json.dumps([1, 2, 3])
    topic_miner.client.models.generate_content.return_value = list_response
    with pytest.raises(ValueError, match="JSON object"):
        topic_miner._generate_json("prompt")


def test_normalize_paper_payload_deduplicates_and_sanitizes(topic_miner):
    payload = {
        "paper_title": "  2024 Exam  ",
        "year": " 2024 ",
        "questions": [
            {
                "question_number": "Q1",
                "topic": " Authentication ",
                "subtopic": " Passwords ",
                "question_summary": " Explain hashing ",
                "evidence_quote": " Use salting ",
                "confidence": "0.91",
            },
            {
                "question_number": 1,
                "topic": "Duplicate",
                "question_summary": "Should be skipped",
            },
            {
                "question_number": 5,
                "topic": "Out of range",
                "question_summary": "Skip",
            },
            {
                "question_number": 2,
                "topic": "Access Control",
                "subtopic": "",
                "question_summary": " Describe RBAC ",
                "evidence_quote": "",
                "confidence": "bad-value",
            },
        ],
    }

    result = topic_miner._normalize_paper_payload({"id": "doc-1", "filename": "paper.pdf"}, payload)

    assert result == {
        "document_id": "doc-1",
        "filename": "paper.pdf",
        "year": "2024",
        "paper_title": "2024 Exam",
        "questions": [
            {
                "question_number": 1,
                "topic": "Authentication",
                "subtopic": "Passwords",
                "question_summary": "Explain hashing",
                "evidence_quote": "Use salting",
                "confidence": 0.91,
            },
            {
                "question_number": 2,
                "topic": "Access Control",
                "subtopic": "Access Control",
                "question_summary": "Describe RBAC",
                "evidence_quote": "Describe RBAC",
                "confidence": 0.5,
            },
        ],
    }


def test_normalize_themes_and_fallback_themes(topic_miner):
    items = [
        {
            "canonical_topic": " Authentication ",
            "question_positions": [2, "Q1", "Q1", 8],
            "frequency": {"papers_with_topic": "2", "total_papers": None},
            "recurring_subtopics": [
                {
                    "name": " Passwords ",
                    "count": "3",
                    "example_questions": [
                        {"paper": "paper1.pdf", "question_number": "1", "summary": "Hash passwords"},
                        {"paper": "paper2.pdf", "question_number": 2, "summary": "Salt passwords"},
                        {"paper": "", "question_number": 3, "summary": "invalid"},
                    ],
                }
            ],
        }
    ]

    normalized = topic_miner._normalize_themes(items, total_papers=4)
    assert normalized == [
        {
            "canonical_topic": "Authentication",
            "question_positions": [1, 2],
            "frequency": {"papers_with_topic": 2, "total_papers": 4},
            "recurring_subtopics": [
                {
                    "name": "Passwords",
                    "count": 3,
                    "example_questions": [
                        {"paper": "paper1.pdf", "question_number": 1, "summary": "Hash passwords"},
                        {"paper": "paper2.pdf", "question_number": 2, "summary": "Salt passwords"},
                    ],
                }
            ],
        }
    ]

    fallback = topic_miner._normalize_themes(
        "not-a-list",
        total_papers=2,
        fallback_papers=[
            {
                "filename": "paper1.pdf",
                "questions": [
                    {
                        "question_number": 1,
                        "topic": "Authentication",
                        "subtopic": "Passwords",
                        "question_summary": "Hash passwords",
                    }
                ],
            },
            {
                "filename": "paper2.pdf",
                "questions": [
                    {
                        "question_number": 2,
                        "topic": "Authentication",
                        "subtopic": "MFA",
                        "question_summary": "Use MFA",
                    }
                ],
            },
        ],
    )

    assert fallback[0]["canonical_topic"] == "Authentication"
    assert fallback[0]["frequency"] == {"papers_with_topic": 2, "total_papers": 2}
    assert fallback[0]["question_positions"] == [1, 2]

