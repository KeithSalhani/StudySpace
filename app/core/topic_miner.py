"""
Topic miner module using Gemini with a two-pass exam-paper analysis pipeline.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class TopicMiner:
    MAX_PAPER_TEXT_CHARS = 120_000
    TARGET_QUESTION_COUNT = 4
    INLINE_PDF_LIMIT_BYTES = 19 * 1024 * 1024

    def __init__(self, document_processor: Any, api_key: str = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        self.document_processor = document_processor
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-3.1-flash-lite-preview"
        self.pipeline_version = "topic-miner-v2-pdf"

        logger.info("Topic Miner initialized with Gemini 3.1 Flash Lite Preview")

    def analyze_folder(
        self,
        folder_name: str,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        if not documents:
            raise ValueError("No exam papers found in this folder")

        extracted_papers: List[Dict[str, Any]] = []
        total_documents = len(documents)

        for index, document in enumerate(documents, start=1):
            filename = document.get("filename") or f"paper-{index}"
            progress = min(75, max(5, int((index - 1) / max(total_documents, 1) * 70)))
            self._emit_progress(progress_callback, f"Reading {filename}", progress)

            try:
                paper_payload = self._extract_paper_topics(folder_name, document)
                extracted_papers.append(paper_payload)
            except Exception as exc:
                logger.warning("Topic miner paper extraction failed for %s: %s", filename, exc)
                extracted_papers.append(
                    {
                        "document_id": document.get("id"),
                        "filename": filename,
                        "year": None,
                        "questions": [],
                        "error": str(exc),
                    }
                )

            progress = min(80, max(10, int(index / max(total_documents, 1) * 80)))
            self._emit_progress(progress_callback, f"Extracted topics from {filename}", progress)

        analyzable_papers = [paper for paper in extracted_papers if paper.get("questions")]
        if not analyzable_papers:
            raise ValueError("Could not extract topics from the selected exam papers")

        self._emit_progress(progress_callback, "Synthesizing recurring topics", 88)

        try:
            synthesis_payload = self._synthesize_folder_topics(folder_name, analyzable_papers)
            themes = self._normalize_themes(synthesis_payload.get("themes"), len(analyzable_papers))
            observations = self._normalize_string_list(synthesis_payload.get("observations"))
        except Exception as exc:
            logger.warning("Falling back to heuristic topic synthesis for %s: %s", folder_name, exc)
            themes = self._fallback_themes(analyzable_papers)
            observations = []

        analyzed_question_count = sum(len(paper.get("questions", [])) for paper in analyzable_papers)
        result = {
            "folder_name": folder_name,
            "paper_count": total_documents,
            "analyzed_paper_count": len(analyzable_papers),
            "analyzed_question_count": analyzed_question_count,
            "papers": extracted_papers,
            "themes": themes,
            "observations": observations,
            "model": self.model_id,
            "pipeline_version": self.pipeline_version,
            "summary": {
                "paper_count": total_documents,
                "analyzed_paper_count": len(analyzable_papers),
                "theme_count": len(themes),
                "question_count": analyzed_question_count,
            },
        }

        self._emit_progress(progress_callback, "Topic mining complete", 100)
        return result

    def _load_document_content(self, document: Dict[str, Any]) -> str:
        file_path = Path(str(document.get("path") or ""))
        if not file_path.exists():
            raise FileNotFoundError(f"Exam paper file not found: {file_path}")

        if str(document.get("filename", "")).lower().endswith(".pdf"):
            content = self.document_processor.process_document(str(file_path))
        else:
            content = file_path.read_text(encoding="utf-8")

        normalized = content.strip()
        if not normalized:
            raise ValueError("Extracted paper content is empty")
        return normalized[: self.MAX_PAPER_TEXT_CHARS]

    def _build_pdf_contents(self, file_path: Path, prompt: str) -> List[Any]:
        if file_path.stat().st_size <= self.INLINE_PDF_LIMIT_BYTES:
            return [
                prompt,
                types.Part.from_bytes(
                    data=file_path.read_bytes(),
                    mime_type="application/pdf",
                ),
            ]

        uploaded_file = self.client.files.upload(
            file=file_path,
            config={"mime_type": "application/pdf"},
        )
        return [prompt, uploaded_file]

    def _build_paper_contents(self, document: Dict[str, Any], prompt: str) -> List[Any]:
        file_path = Path(str(document.get("path") or ""))
        if not file_path.exists():
            raise FileNotFoundError(f"Exam paper file not found: {file_path}")

        filename = str(document.get("filename", "")).lower()
        if filename.endswith(".pdf"):
            return self._build_pdf_contents(file_path, prompt)

        content = self._load_document_content(document)
        return [
            f"""{prompt}

Plain text fallback for a non-PDF exam document:
{content}
"""
        ]

    def _extract_paper_topics(
        self,
        folder_name: str,
        document: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = f"""You are mining recurring exam themes for a revision workspace.

You will be given one exam paper from the folder "{folder_name}" as a PDF document or equivalent source file.
Use the full document, including layout cues, headings, tables, and any visible question numbering.
Focus only on Questions 1 to {self.TARGET_QUESTION_COUNT}.

Return valid JSON with this exact shape:
{{
  "paper_title": "string",
  "year": "string or null",
  "questions": [
    {{
      "question_number": 1,
      "topic": "short canonical topic label",
      "subtopic": "more specific recurring subtopic",
      "question_summary": "one sentence describing the ask",
      "evidence_quote": "short quote copied from the paper",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- Ignore questions beyond Question {self.TARGET_QUESTION_COUNT}.
- Keep topic labels stable and concise.
- Use confidence between 0 and 1.
- If a question number cannot be identified reliably, omit it.
- Only include questions supported by the source document.
- Do not invent question text.
- Prefer the visible wording from the paper over paraphrase when choosing evidence quotes.

Filename: {document.get("filename") or "Unknown"}
"""

        response_payload = self._generate_json(self._build_paper_contents(document, prompt))
        return self._normalize_paper_payload(document, response_payload)

    def _synthesize_folder_topics(
        self,
        folder_name: str,
        papers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = f"""You are synthesizing recurring topics across exam papers in the folder "{folder_name}".

You are given structured topic extractions from multiple papers.

Return valid JSON with this exact shape:
{{
  "themes": [
    {{
      "canonical_topic": "stable theme name",
      "question_positions": [1, 2],
      "frequency": {{
        "papers_with_topic": 0,
        "total_papers": 0
      }},
      "recurring_subtopics": [
        {{
          "name": "specific recurring subtopic",
          "count": 0,
          "example_questions": [
            {{
              "paper": "filename.pdf",
              "question_number": 1,
              "summary": "short summary"
            }}
          ]
        }}
      ]
    }}
  ],
  "observations": [
    "optional short note"
  ]
}}

Rules:
- Merge near-duplicate topics into one canonical topic.
- Rank themes by recurrence, highest first.
- Only use evidence present in the extracted records.
- Keep canonical topics broad enough to cover repeats but not so broad that unrelated areas merge.
- Keep example questions short.

Paper records:
{json.dumps(papers, indent=2)}
"""

        return self._generate_json(prompt)

    def _generate_json(self, contents: Any) -> Dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config={"response_mime_type": "application/json"},
        )

        if not getattr(response, "text", None):
            raise ValueError("Empty response from Gemini")

        parsed = self._parse_json_text(response.text)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini did not return a JSON object")
        return parsed

    @staticmethod
    def _parse_json_text(payload: str) -> Any:
        normalized = payload.strip()
        if normalized.startswith("```"):
            normalized = re.sub(r"^```(?:json)?\s*", "", normalized)
            normalized = re.sub(r"\s*```$", "", normalized)
        return json.loads(normalized)

    def _normalize_paper_payload(
        self,
        document: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        seen_numbers = set()
        questions: List[Dict[str, Any]] = []

        for item in payload.get("questions") or []:
            if not isinstance(item, dict):
                continue

            question_number = self._normalize_question_number(item.get("question_number"))
            if not question_number or question_number in seen_numbers:
                continue

            topic = self._clean_label(item.get("topic"))
            subtopic = self._clean_label(item.get("subtopic"))
            summary = self._clean_text(item.get("question_summary"))
            evidence_quote = self._clean_text(item.get("evidence_quote"))
            if not topic or not summary:
                continue

            questions.append(
                {
                    "question_number": question_number,
                    "topic": topic,
                    "subtopic": subtopic or topic,
                    "question_summary": summary,
                    "evidence_quote": evidence_quote or summary,
                    "confidence": self._normalize_confidence(item.get("confidence")),
                }
            )
            seen_numbers.add(question_number)

        questions.sort(key=lambda item: item["question_number"])
        return {
            "document_id": document.get("id"),
            "filename": document.get("filename"),
            "year": self._clean_label(payload.get("year")),
            "paper_title": self._clean_text(payload.get("paper_title")) or document.get("filename"),
            "questions": questions,
        }

    def _normalize_themes(self, items: Any, total_papers: int) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return self._fallback_themes([])

        themes: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            canonical_topic = self._clean_label(item.get("canonical_topic"))
            if not canonical_topic:
                continue

            frequency = item.get("frequency") if isinstance(item.get("frequency"), dict) else {}
            subtopics: List[Dict[str, Any]] = []
            for subtopic in item.get("recurring_subtopics") or []:
                if not isinstance(subtopic, dict):
                    continue
                name = self._clean_label(subtopic.get("name"))
                if not name:
                    continue
                examples = []
                for example in subtopic.get("example_questions") or []:
                    if not isinstance(example, dict):
                        continue
                    paper = self._clean_text(example.get("paper"))
                    summary = self._clean_text(example.get("summary"))
                    question_number = self._normalize_question_number(example.get("question_number"))
                    if not paper or not summary or not question_number:
                        continue
                    examples.append(
                        {
                            "paper": paper,
                            "question_number": question_number,
                            "summary": summary,
                        }
                    )

                subtopics.append(
                    {
                        "name": name,
                        "count": self._normalize_count(subtopic.get("count")),
                        "example_questions": examples[:3],
                    }
                )

            themes.append(
                {
                    "canonical_topic": canonical_topic,
                    "question_positions": self._normalize_question_positions(item.get("question_positions")),
                    "frequency": {
                        "papers_with_topic": self._normalize_count(frequency.get("papers_with_topic")),
                        "total_papers": self._normalize_count(frequency.get("total_papers")) or total_papers,
                    },
                    "recurring_subtopics": subtopics,
                }
            )

        themes.sort(
            key=lambda item: (
                -item["frequency"]["papers_with_topic"],
                item["canonical_topic"].lower(),
            )
        )
        return themes

    def _fallback_themes(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        total_papers = len(papers)

        for paper in papers:
            seen_topics = set()
            for question in paper.get("questions", []):
                topic = self._clean_label(question.get("topic"))
                if not topic:
                    continue

                key = topic.lower()
                if key not in grouped:
                    grouped[key] = {
                        "canonical_topic": topic,
                        "papers_with_topic": 0,
                        "question_positions": set(),
                        "subtopics": {},
                    }

                bucket = grouped[key]
                bucket["question_positions"].add(question.get("question_number"))
                if key not in seen_topics:
                    bucket["papers_with_topic"] += 1
                    seen_topics.add(key)

                subtopic_name = self._clean_label(question.get("subtopic")) or topic
                subtopic = bucket["subtopics"].setdefault(
                    subtopic_name.lower(),
                    {
                        "name": subtopic_name,
                        "count": 0,
                        "example_questions": [],
                    },
                )
                subtopic["count"] += 1
                if len(subtopic["example_questions"]) < 3:
                    subtopic["example_questions"].append(
                        {
                            "paper": paper.get("filename"),
                            "question_number": question.get("question_number"),
                            "summary": question.get("question_summary"),
                        }
                    )

        themes = []
        for bucket in grouped.values():
            subtopics = sorted(
                bucket["subtopics"].values(),
                key=lambda item: (-item["count"], item["name"].lower()),
            )
            themes.append(
                {
                    "canonical_topic": bucket["canonical_topic"],
                    "question_positions": sorted(
                        position for position in bucket["question_positions"] if position
                    ),
                    "frequency": {
                        "papers_with_topic": bucket["papers_with_topic"],
                        "total_papers": total_papers,
                    },
                    "recurring_subtopics": subtopics[:5],
                }
            )

        themes.sort(
            key=lambda item: (
                -item["frequency"]["papers_with_topic"],
                item["canonical_topic"].lower(),
            )
        )
        return themes

    @staticmethod
    def _emit_progress(
        progress_callback: Optional[Callable[[str, int], None]],
        stage: str,
        progress: int,
    ) -> None:
        if progress_callback:
            progress_callback(stage, max(0, min(100, int(progress))))

    @staticmethod
    def _clean_label(value: Any) -> Optional[str]:
        text = " ".join(str(value or "").split()).strip()
        return text or None

    @staticmethod
    def _clean_text(value: Any) -> Optional[str]:
        text = " ".join(str(value or "").split()).strip()
        return text or None

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.5
        return round(max(0.0, min(1.0, numeric)), 2)

    @staticmethod
    def _normalize_count(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _normalize_question_number(cls, value: Any) -> Optional[int]:
        if isinstance(value, int):
            return value if 1 <= value <= cls.TARGET_QUESTION_COUNT else None

        text = cls._clean_text(value)
        if not text:
            return None

        match = re.search(r"\d+", text)
        if not match:
            return None

        number = int(match.group(0))
        if 1 <= number <= cls.TARGET_QUESTION_COUNT:
            return number
        return None

    @classmethod
    def _normalize_question_positions(cls, value: Any) -> List[int]:
        if not isinstance(value, list):
            return []

        positions = []
        for item in value:
            question_number = cls._normalize_question_number(item)
            if question_number and question_number not in positions:
                positions.append(question_number)
        return sorted(positions)

    @staticmethod
    def _normalize_string_list(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        items = []
        for item in value:
            text = " ".join(str(item or "").split()).strip()
            if text:
                items.append(text)
        return items
