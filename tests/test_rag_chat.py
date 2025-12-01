import pytest
from unittest.mock import MagicMock, patch
from rag_chat import RAGChat

@pytest.fixture
def mock_vector_store():
    return MagicMock()

@pytest.fixture
def mock_genai():
    with patch('rag_chat.genai') as mock:
        yield mock

@pytest.fixture
def rag_chat(mock_vector_store, mock_genai):
    return RAGChat(mock_vector_store, api_key="test_key")

def test_chat_success(rag_chat, mock_vector_store, mock_genai):
    # Setup
    mock_vector_store.get_relevant_context.return_value = ("Context info", [{"source": "doc1"}])
    
    mock_model = mock_genai.GenerativeModel.return_value
    mock_response = MagicMock()
    mock_response.text = "AI Response"
    mock_model.generate_content.return_value = mock_response
    
    # Execute
    response, sources = rag_chat.chat("Hello")
    
    # Verify
    assert response == "AI Response"
    assert len(sources) == 1
    mock_vector_store.get_relevant_context.assert_called_with("Hello")
    mock_model.generate_content.assert_called_once()

def test_chat_empty_response(rag_chat, mock_vector_store, mock_genai):
    # Setup
    mock_vector_store.get_relevant_context.return_value = ("Context", [])
    mock_model = mock_genai.GenerativeModel.return_value
    mock_response = MagicMock()
    mock_response.text = ""  # Empty response
    mock_model.generate_content.return_value = mock_response
    
    # Execute & Verify
    with pytest.raises(ValueError, match="Empty response"):
        rag_chat.chat("Hello")

def test_create_prompt_with_context(rag_chat):
    msg = "Question?"
    ctx = "Relevant info."
    prompt = rag_chat._create_prompt(msg, ctx)
    
    assert "Question?" in prompt
    assert "Relevant info." in prompt
    assert "relevant information from the student's documents" in prompt

def test_create_prompt_no_context(rag_chat):
    msg = "Question?"
    ctx = ""
    prompt = rag_chat._create_prompt(msg, ctx)
    
    assert "Question?" in prompt
    assert "no relevant context was found" in prompt

