"""
Study set generator using Gemini.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from google import genai

logger = logging.getLogger(__name__)


ALLOWED_STUDY_SET_TYPES = {"flashcards", "mcq_quiz", "written_quiz", "mixed_practice"}


class StudySetGenerator:
    def __init__(self, processed_dir: Path, api_key: str = None):
        self.processed_dir = processed_dir
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-3.1-flash-lite-preview"
        logger.info("Study Set Generator initialized with Gemini 3.1 Flash Lite Preview")

    def generate_study_set(
        self,
        filename: str,
        study_type: str,
        num_items: int = 10,
        difficulty: str = "Medium",
        document_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        normalized_type = study_type.strip().lower()
        if normalized_type not in ALLOWED_STUDY_SET_TYPES:
            raise ValueError("Unsupported study set type")

        md_path = document_path or (self.processed_dir / f"{filename}.md")
        if not md_path.exists():
            raise FileNotFoundError(f"Processed document not found: {md_path}")

        with open(md_path, "r", encoding="utf-8") as file:
            content = file.read()

        if not content.strip():
            raise ValueError("Document content is empty")

        bounded_count = max(1, min(int(num_items), 20))
        prompt = self._create_prompt(content, normalized_type, bounded_count, difficulty)
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )

        if not response.text:
            raise ValueError("Empty response from Gemini")

        payload = json.loads(response.text)
        return self._normalize_payload(payload, normalized_type)

    def _create_prompt(self, content: str, study_type: str, num_items: int, difficulty: str) -> str:
        type_instructions = {
            "flashcards": (
                "Create flashcards for spaced repetition. Each item must have type 'flashcard', "
                "front, and back."
            ),
            "mcq_quiz": (
                "Create multiple-choice questions. Each item must have type 'mcq', question, "
                "exactly four options, correct_answer matching one option exactly, and explanation."
            ),
            "written_quiz": (
                "Create written self-check questions. Each item must have type 'written', prompt, "
                "model_answer, and rubric. Do not ask for grading metadata."
            ),
            "mixed_practice": (
                "Create a balanced mix of flashcards, multiple-choice questions, and written "
                "self-check questions. Use item type 'flashcard', 'mcq', or 'written' and the "
                "same fields required for each type."
            ),
        }

        return f"""You are an expert educator creating saved study material.

Study set type: {study_type}
Difficulty: {difficulty}
Number of items: {num_items}

{type_instructions[study_type]}

Return only a valid JSON object with this structure:
{{
  "title": "Concise study set title",
  "items": [
    {{
      "id": 1,
      "type": "flashcard",
      "front": "Term or prompt",
      "back": "Answer or explanation"
    }},
    {{
      "id": 2,
      "type": "mcq",
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Why the answer is correct."
    }},
    {{
      "id": 3,
      "type": "written",
      "prompt": "Written question prompt",
      "model_answer": "Strong answer students can compare against",
      "rubric": "Key points expected in the answer"
    }}
  ]
}}

Only include item shapes appropriate for the requested study set type. Base every item on the source text.

Text content:
{content[:30000]}
"""

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any], study_type: str) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Gemini response must be a JSON object")

        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise ValueError("Gemini response did not include study set items")

        items = []
        for index, raw_item in enumerate(raw_items, start=1):
            if not isinstance(raw_item, dict):
                continue
            item = dict(raw_item)
            item["id"] = item.get("id") or index
            item_type = str(item.get("type") or "").strip().lower()

            if study_type == "flashcards":
                item_type = "flashcard"
            elif study_type == "mcq_quiz":
                item_type = "mcq"
            elif study_type == "written_quiz":
                item_type = "written"

            if item_type not in {"flashcard", "mcq", "written"}:
                continue

            item["type"] = item_type
            items.append(item)

        if not items:
            raise ValueError("Gemini response did not include valid study set items")

        return {
            "title": str(payload.get("title") or "Study Set").strip() or "Study Set",
            "items": items,
        }
