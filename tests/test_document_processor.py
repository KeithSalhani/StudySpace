import pytest
from unittest.mock import MagicMock, patch
from app.core.ingestion import DocumentProcessor

@pytest.fixture
def mock_markitdown():
    with patch('app.core.ingestion.DocumentConverter') as MockMarkItDown:
        yield MockMarkItDown

@pytest.fixture
def mock_classifier():
    with patch('app.core.ingestion.Classifier') as MockClassifier:
        yield MockClassifier

@pytest.fixture
def document_processor(mock_markitdown, mock_classifier):
    return DocumentProcessor()

def test_process_document_success(document_processor, mock_markitdown):
    # Setup
    mock_instance = mock_markitdown.return_value
    mock_result = MagicMock()
    mock_result.document.export_to_markdown.return_value = "Processed content"
    mock_instance.convert.return_value = mock_result
    
    with patch('pathlib.Path.exists', return_value=True):
        # Execute
        result = document_processor.process_document("test.pdf")
        
        # Verify
        assert result == "Processed content"
        mock_instance.convert.assert_called_once_with("test.pdf")

def test_process_document_file_not_found(document_processor):
    with patch('pathlib.Path.exists', return_value=False):
        with pytest.raises(FileNotFoundError):
            document_processor.process_document("nonexistent.pdf")

def test_process_document_rejects_unsupported_extension(document_processor):
    with patch('pathlib.Path.exists', return_value=True):
        with pytest.raises(ValueError, match="Unsupported file type"):
            document_processor.process_document("archive.zip")

def test_classify_content_success(document_processor, mock_classifier):
    # Setup
    mock_instance = mock_classifier.return_value
    mock_instance.classify.return_value = {'labels': ['Security', 'AI'], 'scores': [0.9, 0.1]}
    
    # Execute
    result = document_processor.classify_content("Some security text", ['Security', 'AI'])
    
    # Verify
    assert result == 'Security'
    mock_instance.classify.assert_called_once()

def test_classify_content_empty_input(document_processor):
    assert document_processor.classify_content("", ['Tag']) is None
    assert document_processor.classify_content("Text", []) is None

def test_classify_content_full_success(document_processor, mock_classifier):
    # Setup
    mock_instance = mock_classifier.return_value
    expected_result = {'labels': ['Security', 'AI'], 'scores': [0.9, 0.1]}
    mock_instance.classify.return_value = expected_result
    
    # Execute
    result = document_processor.classify_content_full("Some security text", ['Security', 'AI'])
    
    # Verify
    assert result == expected_result

def test_process_text_file_success(document_processor):
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_file.read.return_value = "Text content"
        mock_file.__enter__.return_value = mock_file
        mock_open.return_value = mock_file
        
        result = document_processor.process_text_file("test.txt")
        assert result == "Text content"

def test_process_document_uses_text_handler_for_txt(document_processor):
    with patch('pathlib.Path.exists', return_value=True):
        with patch.object(document_processor, 'process_text_file', return_value="Text content") as process_text:
            result = document_processor.process_document("test.txt")

    assert result == "Text content"
    process_text.assert_called_once_with("test.txt")

def test_supports_file_includes_audio_and_text_extensions(document_processor):
    assert document_processor.supports_file("lecture.txt") is True
    assert document_processor.supports_file("lecture.mp3") is True
    assert document_processor.supports_file("lecture.wav") is True
    assert document_processor.supports_file("archive.zip") is False
