import pytest
from unittest.mock import patch
from classification import Classifier

@pytest.fixture
def classifier():
    with patch('classification.pipeline') as mock_pipeline:
        yield Classifier()

def test_classify_success(classifier):
    # Setup
    mock_pipeline = classifier.classifier
    expected_result = {'labels': ['A', 'B'], 'scores': [0.8, 0.2]}
    mock_pipeline.return_value = expected_result
    
    # Execute
    result = classifier.classify("some text", ['A', 'B'])
    
    # Verify
    assert result == expected_result
    mock_pipeline.assert_called_once()
    
    # Verify truncation logic (should not be triggered for short text)
    args, _ = mock_pipeline.call_args
    assert args[0] == "some text"

def test_classify_truncation(classifier):
    # Setup
    long_text = "x" * 3000
    mock_pipeline = classifier.classifier
    
    # Execute
    classifier.classify(long_text, ['A'])
    
    # Verify truncation
    args, _ = mock_pipeline.call_args
    assert len(args[0]) == 2000

