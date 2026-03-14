"""
Metadata Extractor module using Gemini
"""
from google import genai
import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MetadataExtractor:
    def __init__(self, api_key: str = None):
        """
        Initialize Metadata Extractor with Gemini
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3.1-flash-lite-preview'
        logger.info("Metadata Extractor initialized")

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract academic metadata from content
        """
        try:
            prompt = f"""Extract academic metadata from the provided markdown text. 
            Identify and return as a JSON object with the following structure:
            {{
                "assessments": [
                    {{"item": "Final Exam", "weight": "60%"}}
                ],
                "deadlines": [
                    {{"event": "Project Submission", "date": "2025-05-12"}}
                ],
                "contacts": [
                    {{"name": "Dr. Smith", "email": "smith@example.edu", "role": "Lecturer"}}
                ]
            }}

            If no information is found for a category, return an empty list for that key.
            Markdown content:
            {content[:30000]}
            """
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            if not response.text:
                return {"assessments": [], "deadlines": [], "contacts": []}
                
            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {"assessments": [], "deadlines": [], "contacts": []}
