"""
Quiz Generator module using Gemini
"""
import google.generativeai as genai
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class QuizGenerator:
    def __init__(self, processed_dir: Path, api_key: str = None):
        """
        Initialize Quiz Generator with Gemini

        Args:
            processed_dir: Directory where processed markdown files are stored
            api_key: Google AI API key
        """
        self.processed_dir = processed_dir
        
        # Set up API key
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        genai.configure(api_key=api_key)
        
        # Initialize Gemini model
        # Using flash for speed/cost, but ensuring it can handle JSON output
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        logger.info("Quiz Generator initialized")

    def generate_quiz(self, filename: str, num_questions: int = 5, difficulty: str = "Medium") -> Dict[str, Any]:
        """
        Generate a quiz from a document

        Args:
            filename: Name of the file (must exist in processed_dir as .md)
            num_questions: Number of questions to generate
            difficulty: Difficulty level (Easy, Medium, Hard)

        Returns:
            Dictionary containing quiz questions
        """
        try:
            # 1. Read the document content
            # The filename might be the original PDF name, so we need to find the corresponding MD file
            # In main.py, we will save it as {filename}.md
            md_path = self.processed_dir / f"{filename}.md"
            
            if not md_path.exists():
                # Fallback: try without .md extension if it was saved differently or check for original filename
                # For now, assume strict naming convention from main.py
                raise FileNotFoundError(f"Processed document not found: {md_path}")
                
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                raise ValueError("Document content is empty")

            # 2. Construct Prompt
            prompt = self._create_quiz_prompt(content, num_questions, difficulty)
            
            # 3. Call Gemini
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # 4. Parse Response
            if not response.text:
                raise ValueError("Empty response from Gemini")
                
            quiz_data = json.loads(response.text)
            return quiz_data

        except Exception as e:
            logger.error(f"Error generating quiz for {filename}: {str(e)}")
            raise

    def _create_quiz_prompt(self, content: str, num_questions: int, difficulty: str) -> str:
        """Create the prompt for quiz generation"""
        return f"""You are an expert educator. Create a {num_questions}-question multiple-choice quiz based on the following text.
        
        Difficulty Level: {difficulty}
        
        The output must be a valid JSON object with the following structure:
        {{
            "title": "Quiz Title",
            "questions": [
                {{
                    "id": 1,
                    "question": "Question text here?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "explanation": "Brief explanation of why this is correct."
                }}
            ]
        }}

        Ensure the questions are relevant to the key concepts in the text.
        
        Text content:
        {content[:30000]}  # Truncate to avoid context limit if necessary, though 2.5 flash has large context
        """
