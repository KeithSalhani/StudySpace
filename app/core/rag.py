"""
RAG chat orchestration with multi-query retrieval and transparent trace data.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from google import genai

from app.db.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGChat:
    QUERY_COUNT = 3
    SEARCH_RESULTS_PER_QUERY = 4
    FUSED_RESULTS_LIMIT = 6
    RRF_K = 60

    def __init__(self, vector_store: VectorStore, api_key: str = None):
        """
        Initialize RAG chat with Gemini.

        Args:
            vector_store: Vector store instance
            api_key: Google AI API key (can also be set via GEMINI_API_KEY env var)
        """
        self.vector_store = vector_store

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be set")

        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-3.1-flash-lite-preview"

        logger.info("RAG Chat initialized with Gemini 3.1 Flash Lite Preview")

    def chat(
        self,
        message: str,
        owner_username: str,
        selected_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message with multi-query RAG.

        Returns:
            Dictionary containing the final answer, source summary, and trace metadata.
        """
        try:
            total_started = time.perf_counter()

            available_tags = self._get_available_tags(owner_username, selected_files)

            planning_started = time.perf_counter()
            planned_queries = self._generate_query_plan(
                message,
                selected_files=selected_files,
                available_tags=available_tags,
            )
            planning_ms = round((time.perf_counter() - planning_started) * 1000, 1)

            retrieval_started = time.perf_counter()
            retrieval_runs = self._retrieve_for_queries(
                planned_queries,
                owner_username=owner_username,
                selected_files=selected_files,
                available_tags=available_tags,
            )
            fused_results = self._fuse_results(retrieval_runs)
            retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 1)

            generation_started = time.perf_counter()
            prompt = self._create_prompt(message, fused_results)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )
            generation_ms = round((time.perf_counter() - generation_started) * 1000, 1)

            if not response.text:
                raise ValueError("Empty response from Gemini")

            total_ms = round((time.perf_counter() - total_started) * 1000, 1)
            sources = self._build_source_summary(fused_results)

            trace = {
                "original_question": message,
                "generated_queries": [
                    {
                        "id": run["query_id"],
                        "text": run["query"],
                        "goal": run["goal"],
                        "module_tag": run["module_tag"],
                        "results_found": len(run["results"]),
                    }
                    for run in retrieval_runs
                ],
                "retrieval_runs": retrieval_runs,
                "fused_results": fused_results,
                "selected_files": selected_files or [],
                "available_tags": available_tags,
                "model": self.model_id,
                "summary": {
                    "queries_used": len(retrieval_runs),
                    "documents_considered": len(
                        {
                            result["filename"]
                            for result in fused_results
                            if result.get("filename")
                        }
                    ),
                    "passages_used": len(fused_results),
                },
                "timings_ms": {
                    "planning": planning_ms,
                    "retrieval": retrieval_ms,
                    "generation": generation_ms,
                    "total": total_ms,
                },
            }

            return {
                "response": response.text,
                "sources": sources,
                "trace": trace,
            }

        except Exception as exc:
            logger.error("Error in chat: %s", exc)
            raise

    def _get_available_tags(
        self,
        owner_username: str,
        selected_files: Optional[List[str]],
    ) -> List[str]:
        documents = self.vector_store.list_documents(owner_username)
        visible_documents = [
            doc
            for doc in documents
            if not selected_files or doc.get("filename") in selected_files
        ]

        tags = {
            (doc.get("tag") or "").strip()
            for doc in visible_documents
            if (doc.get("tag") or "").strip() and (doc.get("tag") or "").strip().lower() != "uncategorized"
        }
        return sorted(tags)

    def _generate_query_plan(
        self,
        message: str,
        selected_files: Optional[List[str]],
        available_tags: List[str],
    ) -> List[Dict[str, Any]]:
        selected_files_label = ", ".join(selected_files or []) or "None"
        tags_label = ", ".join(available_tags) or "None"
        prompt = f"""You are planning retrieval for a student study assistant.
Generate exactly {self.QUERY_COUNT} complementary search queries for the user's question.

Return JSON with this exact shape:
{{
  "queries": [
    {{
      "text": "search query",
      "goal": "what this query is trying to retrieve",
      "module_tag": "one exact tag from the allowed list or null"
    }}
  ]
}}

Rules:
- The queries should be different from each other and cover different angles.
- Prefer short, search-friendly phrasing.
- If a module tag would help retrieval, choose one exact tag from the allowed list.
- If no tag is clearly appropriate, use null for module_tag.
- Never invent tags outside the allowed list.

Selected files: {selected_files_label}
Allowed module tags: {tags_label}
User question: {message}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            plan = json.loads(response.text or "{}")
            normalized = self._normalize_query_plan(plan.get("queries"), available_tags, message)
            if normalized:
                return normalized
        except Exception as exc:
            logger.warning("Falling back to heuristic query plan: %s", exc)

        return self._fallback_query_plan(message, available_tags)

    def _normalize_query_plan(
        self,
        items: Any,
        available_tags: List[str],
        fallback_message: str,
    ) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []

        normalized: List[Dict[str, Any]] = []
        seen_queries = set()

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            text = " ".join(str(item.get("text", "")).split())
            if not text:
                continue

            dedupe_key = text.lower()
            if dedupe_key in seen_queries:
                continue
            seen_queries.add(dedupe_key)

            module_tag = self._normalize_module_tag(item.get("module_tag"), available_tags)
            normalized.append(
                {
                    "query_id": f"q{len(normalized) + 1}",
                    "text": text,
                    "goal": " ".join(str(item.get("goal", "")).split()) or f"Explore angle {index + 1}",
                    "module_tag": module_tag,
                }
            )

            if len(normalized) == self.QUERY_COUNT:
                break

        if len(normalized) < self.QUERY_COUNT:
            fallbacks = self._fallback_query_plan(fallback_message, available_tags)
            for fallback in fallbacks:
                if fallback["text"].lower() not in seen_queries:
                    normalized.append(fallback)
                    seen_queries.add(fallback["text"].lower())
                if len(normalized) == self.QUERY_COUNT:
                    break

        return normalized[: self.QUERY_COUNT]

    def _fallback_query_plan(
        self,
        message: str,
        available_tags: List[str],
    ) -> List[Dict[str, Any]]:
        base_message = message.strip() or "student study question"
        inferred_tag = self._infer_module_tag(base_message, available_tags)
        variants = [
            base_message,
            f"Core concepts and definitions for {base_message}",
            f"Specific examples, procedures, and evidence for {base_message}",
        ]

        return [
            {
                "query_id": f"q{index + 1}",
                "text": variant,
                "goal": goal,
                "module_tag": inferred_tag,
            }
            for index, (variant, goal) in enumerate(
                zip(
                    variants,
                    [
                        "Retrieve the most directly relevant passages.",
                        "Find foundational explanations and definitions.",
                        "Find concrete supporting details and examples.",
                    ],
                )
            )
        ]

    def _infer_module_tag(self, message: str, available_tags: List[str]) -> Optional[str]:
        lowered_message = message.lower()
        for tag in available_tags:
            if tag.lower() in lowered_message:
                return tag
        return None

    def _normalize_module_tag(
        self,
        value: Any,
        available_tags: List[str],
    ) -> Optional[str]:
        if not isinstance(value, str):
            return None

        candidate = value.strip()
        if not candidate:
            return None

        lowered = candidate.lower()
        for tag in available_tags:
            if tag.lower() == lowered:
                return tag
        return None

    def _retrieve_for_queries(
        self,
        planned_queries: List[Dict[str, Any]],
        owner_username: str,
        selected_files: Optional[List[str]],
        available_tags: List[str],
    ) -> List[Dict[str, Any]]:
        retrieval_runs: List[Dict[str, Any]] = []

        for item in planned_queries:
            module_tag = self._normalize_module_tag(item.get("module_tag"), available_tags)
            active_tags = [module_tag] if module_tag and not selected_files else None
            raw_results = self.vector_store.search(
                item["text"],
                owner_username=owner_username,
                n_results=self.SEARCH_RESULTS_PER_QUERY,
                selected_files=selected_files,
                selected_tags=active_tags,
            )

            retrieval_runs.append(
                {
                    "query_id": item["query_id"],
                    "query": item["text"],
                    "goal": item["goal"],
                    "module_tag": module_tag,
                    "results": [
                        self._serialize_search_result(result, rank=index + 1, query_id=item["query_id"])
                        for index, result in enumerate(raw_results)
                    ],
                }
            )

        return retrieval_runs

    def _serialize_search_result(
        self,
        result: Dict[str, Any],
        rank: int,
        query_id: str,
    ) -> Dict[str, Any]:
        metadata = result.get("metadata") or {}
        text = result.get("document") or ""

        return {
            "id": result.get("id"),
            "query_id": query_id,
            "rank": rank,
            "doc_id": metadata.get("doc_id"),
            "filename": metadata.get("filename", "Unknown"),
            "chunk_index": metadata.get("chunk_index"),
            "distance": result.get("distance"),
            "tag": metadata.get("tag"),
            "snippet": self._make_snippet(text),
            "content": text,
            "kept_in_fusion": False,
        }

    def _fuse_results(self, retrieval_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fused_by_id: Dict[str, Dict[str, Any]] = {}

        for run in retrieval_runs:
            for result in run["results"]:
                result_id = result.get("id")
                if not result_id:
                    continue

                fused_entry = fused_by_id.setdefault(
                    result_id,
                    {
                        "id": result_id,
                        "doc_id": result.get("doc_id"),
                        "filename": result.get("filename"),
                        "chunk_index": result.get("chunk_index"),
                        "distance": result.get("distance"),
                        "tag": result.get("tag"),
                        "snippet": result.get("snippet"),
                        "content": result.get("content"),
                        "query_ids": [],
                        "fused_score": 0.0,
                        "best_rank": result["rank"],
                    },
                )

                fused_entry["query_ids"].append(run["query_id"])
                fused_entry["best_rank"] = min(fused_entry["best_rank"], result["rank"])
                if fused_entry.get("distance") is None or (
                    result.get("distance") is not None and result["distance"] < fused_entry["distance"]
                ):
                    fused_entry["distance"] = result["distance"]
                fused_entry["fused_score"] += 1.0 / (self.RRF_K + result["rank"])

        fused_results = sorted(
            fused_by_id.values(),
            key=lambda item: (
                -item["fused_score"],
                item["distance"] if item.get("distance") is not None else float("inf"),
                item.get("filename") or "",
            ),
        )[: self.FUSED_RESULTS_LIMIT]

        kept_ids = {item["id"] for item in fused_results}
        for run in retrieval_runs:
            for result in run["results"]:
                result["kept_in_fusion"] = result.get("id") in kept_ids

        for index, item in enumerate(fused_results, start=1):
            item["source_id"] = f"S{index}"
            item["query_ids"] = sorted(set(item["query_ids"]))
            item["content"] = item.get("content") or ""

        return fused_results

    def _build_source_summary(self, fused_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "source_id": item["source_id"],
                "doc_id": item.get("doc_id"),
                "filename": item.get("filename", "Unknown"),
                "chunk_index": item.get("chunk_index"),
                "distance": item.get("distance"),
                "tag": item.get("tag"),
            }
            for item in fused_results
        ]

    def _create_prompt(self, message: str, fused_results: List[Dict[str, Any]]) -> str:
        evidence_context = self._build_evidence_context(fused_results)

        if evidence_context:
            return f"""You are a helpful AI assistant for students studying academic modules.
Answer the user's question using the retrieved evidence below.

Rules:
- Base the answer on the evidence when possible.
- Cite evidence ids inline like [S1] when making factual claims.
- If the evidence is incomplete, say what is missing and clearly separate any general guidance from document-backed points.
- Keep the answer clear, concise, and useful.

Evidence:
{evidence_context}

User question:
{message}
"""

        return f"""You are a helpful AI assistant for students.
No relevant evidence was retrieved from the user's uploaded documents.

User question:
{message}

Answer helpfully, but clearly note that the uploaded documents did not provide direct supporting evidence."""

    def _build_evidence_context(self, fused_results: List[Dict[str, Any]]) -> str:
        parts = []
        for item in fused_results:
            header_bits = [
                item["source_id"],
                item.get("filename", "Unknown"),
                f"chunk {item.get('chunk_index', '?')}",
            ]
            if item.get("tag"):
                header_bits.append(f"module {item['tag']}")
            header = " | ".join(header_bits)
            parts.append(f"[{header}]\n{item.get('content', '').strip()}")
        return "\n\n".join(parts)

    def _make_snippet(self, text: str, limit: int = 220) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 1].rstrip()}…"
