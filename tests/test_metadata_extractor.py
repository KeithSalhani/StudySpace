import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.metadata_extractor import MetadataExtractor


@pytest.fixture
def mock_genai():
    with patch("app.core.metadata_extractor.genai") as mock:
        yield mock


def test_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError):
        MetadataExtractor()


def test_extract_metadata_parses_json_response(mock_genai):
    mock_response = MagicMock()
    expected = {
        "assessments": [{"item": "Exam", "weight": "60%"}],
        "deadlines": [{"event": "Project", "date": "2026-05-12"}],
        "contacts": [{"name": "Dr. Smith", "email": "smith@example.edu", "role": "Lecturer"}],
    }
    mock_response.text = json.dumps(expected)
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    extractor = MetadataExtractor(api_key="test_key")
    result = extractor.extract_metadata("A" * 40000)

    assert result == expected
    _, kwargs = mock_genai.Client.return_value.models.generate_content.call_args
    assert kwargs["model"] == "gemini-3.1-flash-lite-preview"
    assert len(kwargs["contents"]) < 31000


def test_extract_metadata_returns_empty_defaults_on_empty_response(mock_genai):
    mock_response = MagicMock()
    mock_response.text = ""
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    extractor = MetadataExtractor(api_key="test_key")

    assert extractor.extract_metadata("content") == {
        "assessments": [],
        "deadlines": [],
        "contacts": [],
    }


def test_extract_metadata_returns_empty_defaults_on_invalid_json(mock_genai):
    mock_response = MagicMock()
    mock_response.text = "{not-json"
    mock_genai.Client.return_value.models.generate_content.return_value = mock_response

    extractor = MetadataExtractor(api_key="test_key")

    assert extractor.extract_metadata("content") == {
        "assessments": [],
        "deadlines": [],
        "contacts": [],
    }
