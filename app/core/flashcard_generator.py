"""
Flashcard Generator module using Gemini
"""
from google import genai
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FlashcardGenerator:
    def __init__(self, processed_dir: Path, api_key: str = None):
        """
        Initialize Flashcard Generator with Gemini

        Args:
            processed_dir: Directory where processed markdown files are stored
            api_key: Google AI API key
        """
        self.processed_dir = processed_dir
        
        # Set up API key
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        # Initialize Google Gen AI client
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-2.0-flash'
        
        logger.info("Flashcard Generator initialized with Gemini 2.0 Flash")

    def generate_flashcards(self, filename: str, num_cards: int = 10) -> Dict[str, Any]:
        """
        Generate flashcards from a document

        Args:
            filename: Name of the file (must exist in processed_dir as .md)
            num_cards: Number of flashcards to generate

        Returns:
            Dictionary containing flashcards
        """
        try:
            # 1. Read the document content
            md_path = self.processed_dir / f"{filename}.md"
            
            if not md_path.exists():
                raise FileNotFoundError(f"Processed document not found: {md_path}")
                
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                raise ValueError("Document content is empty")

            # 2. Construct Prompt
            prompt = self._create_flashcard_prompt(content, num_cards)
            
            # 3. Call Gemini
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            # 4. Parse Response
            if not response.text:
                raise ValueError("Empty response from Gemini")
                
            flashcard_data = json.loads(response.text)
            return flashcard_data

        except Exception as e:
            logger.error(f"Error generating flashcards for {filename}: {str(e)}")
            raise

    def _create_flashcard_prompt(self, content: str, num_cards: int) -> str:
        """Create the prompt for flashcard generation"""
        return f"""You are an expert educator. Create {num_cards} flashcards based on the key concepts in the following text.
        
        The output must be a valid JSON object with the following structure:
        {{
            "title": "Flashcard Set Title",
            "cards": [
                {{
                    "id": 1,
                    "front": "Term or Concept",
                    "back": "Definition or Explanation"
                }}
            ]
        }}

        Ensure the cards cover the most important information and are suitable for spaced repetition.
        
        Text content:
        {content[:30000]}
        """
