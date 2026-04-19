import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.study_set_generator import StudySetGenerator


@pytest.fixture
def mock_genai():
    with patch("app.core.study_set_generator.genai") as mock:
        yield mock


def test_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError):
        StudySetGenerator(Path("/tmp/processed"))


def test_generate_study_set_normalizes_type_and_bounds_item_count(tmp_path, mock_genai):
    document = tmp_path / "lecture.pdf.md"
    document.write_text("Important revision content", encoding="utf-8")

    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "title": "  Security Set  ",
            "items": [
                {"type": "ignored", "front": "Q1", "back": "A1"},
                {"id": 9, "type": "flashcard", "front": "Q2", "back": "A2"},
            ],
        }
    )
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    generator = StudySetGenerator(tmp_path, api_key="test_key")
    result = generator.generate_study_set("lecture.pdf", " flashcards ", num_items=50, difficulty="Hard")

    assert result == {
        "title": "Security Set",
        "items": [
            {"id": 1, "type": "flashcard", "front": "Q1", "back": "A1"},
            {"id": 9, "type": "flashcard", "front": "Q2", "back": "A2"},
        ],
    }

    _, kwargs = mock_genai.Client.return_value.models.generate_content.call_args
    assert kwargs["model"] == "gemini-3.1-flash-lite-preview"
    assert kwargs["config"] == {"response_mime_type": "application/json"}
    assert "Study set type: flashcards" in kwargs["contents"]
    assert "Number of items: 20" in kwargs["contents"]
    assert "Difficulty: Hard" in kwargs["contents"]


def test_generate_study_set_uses_explicit_document_path_for_mixed_practice(tmp_path, mock_genai):
    document = tmp_path / "custom.md"
    document.write_text("Custom content", encoding="utf-8")

    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "items": [
                {"type": "flashcard", "front": "Front", "back": "Back"},
                {"type": "mcq", "question": "Q?", "options": ["A", "B", "C", "D"], "correct_answer": "A"},
                {"type": "written", "prompt": "Explain", "model_answer": "Because", "rubric": "Mention X"},
                {"type": "unknown"},
            ]
        }
    )
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    generator = StudySetGenerator(tmp_path, api_key="test_key")
    result = generator.generate_study_set(
        "ignored.pdf",
        "mixed_practice",
        num_items=0,
        document_path=document,
    )

    assert result["title"] == "Study Set"
    assert [item["id"] for item in result["items"]] == [1, 2, 3]
    assert [item["type"] for item in result["items"]] == ["flashcard", "mcq", "written"]

    _, kwargs = mock_genai.Client.return_value.models.generate_content.call_args
    assert "Number of items: 1" in kwargs["contents"]
    assert "Custom content" in kwargs["contents"]


@pytest.mark.parametrize("study_type", ["mcq_quiz", "written_quiz"])
def test_generate_study_set_forced_item_type_by_requested_mode(tmp_path, mock_genai, study_type):
    document = tmp_path / "notes.md"
    document.write_text("Course notes", encoding="utf-8")

    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "title": "Mode specific",
            "items": [{"type": "flashcard", "question": "Q?", "prompt": "Explain"}],
        }
    )
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    generator = StudySetGenerator(tmp_path, api_key="test_key")
    result = generator.generate_study_set("notes", study_type)

    expected_type = "mcq" if study_type == "mcq_quiz" else "written"
    assert result["items"][0]["type"] == expected_type


def test_generate_study_set_rejects_invalid_inputs(tmp_path, mock_genai):
    generator = StudySetGenerator(tmp_path, api_key="test_key")

    with pytest.raises(ValueError, match="Unsupported study set type"):
        generator.generate_study_set("notes", "summary")

    missing_path = tmp_path / "notes.md"
    with pytest.raises(FileNotFoundError):
        generator.generate_study_set("notes", "flashcards", document_path=missing_path)

    empty_path = tmp_path / "empty.md"
    empty_path.write_text("   ", encoding="utf-8")
    with pytest.raises(ValueError, match="Document content is empty"):
        generator.generate_study_set("notes", "flashcards", document_path=empty_path)

    mock_response = MagicMock()
    mock_response.text = ""
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response
    valid_path = tmp_path / "valid.md"
    valid_path.write_text("content", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty response from Gemini"):
        generator.generate_study_set("notes", "flashcards", document_path=valid_path)


def test_normalize_payload_validates_shape_and_filters_invalid_items():
    with pytest.raises(ValueError, match="JSON object"):
        StudySetGenerator._normalize_payload([], "flashcards")

    with pytest.raises(ValueError, match="study set items"):
        StudySetGenerator._normalize_payload({}, "flashcards")

    with pytest.raises(ValueError, match="valid study set items"):
        StudySetGenerator._normalize_payload({"items": [{"type": "bad"}]}, "mixed_practice")

