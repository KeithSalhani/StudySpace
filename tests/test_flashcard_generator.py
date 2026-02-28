import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
from pathlib import Path
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.flashcard_generator import FlashcardGenerator

class TestFlashcardGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_processed_dir = Path("/tmp/processed")
        self.mock_api_key = "test_key"
        
        # Patch google.generativeai
        self.patcher = patch('app.core.flashcard_generator.genai')
        self.mock_genai = self.patcher.start()
        
        self.flashcard_generator = FlashcardGenerator(self.mock_processed_dir, self.mock_api_key)

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        """Test initialization"""
        self.mock_genai.configure.assert_called_with(api_key="test_key")
        self.mock_genai.GenerativeModel.assert_called_with('gemini-2.5-flash')

    @patch('builtins.open', new_callable=mock_open, read_data="Test content")
    @patch('pathlib.Path.exists')
    def test_generate_flashcards_success(self, mock_exists, mock_file):
        """Test successful flashcard generation"""
        mock_exists.return_value = True
        
        # Mock Gemini response
        mock_response = MagicMock()
        expected_flashcards = {
            "title": "Test Flashcards",
            "cards": [
                {
                    "id": 1,
                    "front": "Term",
                    "back": "Definition"
                }
            ]
        }
        mock_response.text = json.dumps(expected_flashcards)
        self.flashcard_generator.model.generate_content.return_value = mock_response

        flashcards = self.flashcard_generator.generate_flashcards("test_doc.pdf")
        
        self.assertEqual(flashcards, expected_flashcards)
        self.flashcard_generator.model.generate_content.assert_called_once()
        
        # Verify prompt contains content
        args, kwargs = self.flashcard_generator.model.generate_content.call_args
        self.assertIn("Test content", args[0])

    @patch('pathlib.Path.exists')
    def test_generate_flashcards_file_not_found(self, mock_exists):
        """Test file not found error"""
        mock_exists.return_value = False
        
        with self.assertRaises(FileNotFoundError):
            self.flashcard_generator.generate_flashcards("nonexistent.pdf")

    @patch('builtins.open', new_callable=mock_open, read_data="")
    @patch('pathlib.Path.exists')
    def test_generate_flashcards_empty_content(self, mock_exists, mock_file):
        """Test empty content error"""
        mock_exists.return_value = True
        
        with self.assertRaises(ValueError):
            self.flashcard_generator.generate_flashcards("empty.pdf")

if __name__ == '__main__':
    unittest.main()
