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

from app.core.workspace_catalog import build_workspace_catalog_snapshot
from app.db.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGChat:
    QUERY_COUNT = 3
    SEARCH_RESULTS_PER_QUERY = 4
    FUSED_RESULTS_LIMIT = 6
    RRF_K = 60
    FULL_DOCUMENT_FETCH_LIMIT = 2

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

            workspace_catalog = self._build_workspace_catalog(owner_username, selected_files)
            available_tags = sorted((workspace_catalog.get("tags") or {}).keys())

            planning_started = time.perf_counter()
            planned_queries = self._generate_query_plan(
                message,
                selected_files=selected_files,
                workspace_catalog=workspace_catalog,
            )
            planning_ms = round((time.perf_counter() - planning_started) * 1000, 1)

            retrieval_started = time.perf_counter()
            retrieval_runs = self._execute_search_plan(
                planned_queries,
                owner_username=owner_username,
                selected_files=selected_files,
                workspace_catalog=workspace_catalog,
            )
            fused_results = self._fuse_results(retrieval_runs)
            retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 1)

            generation_started = time.perf_counter()
            response_payload = self._generate_response_with_document_fallback(
                message=message,
                owner_username=owner_username,
                fused_results=fused_results,
            )
            generation_ms = round((time.perf_counter() - generation_started) * 1000, 1)

            total_ms = round((time.perf_counter() - total_started) * 1000, 1)
            sources = self._build_source_summary(
                fused_results,
                full_document_sources=response_payload["full_document_sources"],
            )

            trace = {
                "original_question": message,
                "generated_queries": [
                    {
                        "id": run["query_id"],
                        "text": run["query"],
                        "goal": run["goal"],
                        "search_mode": run["search_mode"],
                        "module_tag": run["module_tag"],
                        "target_files": run["target_files"],
                        "results_found": len(run["results"]),
                    }
                    for run in retrieval_runs
                ],
                "retrieval_runs": retrieval_runs,
                "fused_results": fused_results,
                "full_document_fetches": response_payload["full_document_fetches"],
                "selected_files": selected_files or [],
                "workspace_catalog": workspace_catalog,
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
                "response": response_payload["response"],
                "sources": sources,
                "trace": trace,
            }

        except Exception as exc:
            logger.error("Error in chat: %s", exc)
            raise

    def _build_workspace_catalog(
        self,
        owner_username: str,
        selected_files: Optional[List[str]],
    ) -> Dict[str, Any]:
        documents = self.vector_store.list_documents(owner_username)
        visible_documents = [
            doc
            for doc in documents
            if not selected_files or doc.get("filename") in selected_files
        ]
        return build_workspace_catalog_snapshot(searchable_documents=visible_documents)

    def _get_catalog_files(self, workspace_catalog: Dict[str, Any]) -> List[str]:
        filenames = []
        seen = set()

        for files in (workspace_catalog.get("tags") or {}).values():
            if not isinstance(files, list):
                continue
            for item in files:
                if isinstance(item, str) and item not in seen:
                    seen.add(item)
                    filenames.append(item)

        for item in workspace_catalog.get("untagged_files") or []:
            if isinstance(item, str) and item not in seen:
                seen.add(item)
                filenames.append(item)

        return sorted(filenames, key=str.lower)

    def _generate_query_plan(
        self,
        message: str,
        selected_files: Optional[List[str]],
        workspace_catalog: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        selected_files_label = ", ".join(selected_files or []) or "None"
        prompt = f"""You are planning search strategy for a student study assistant.
Generate 1 to {self.QUERY_COUNT} search steps for the user's question.

Return JSON with this exact shape:
{{
  "queries": [
    {{
      "text": "search query or document-review label",
      "goal": "what this step is trying to retrieve",
      "search_mode": "unfocused | focused",
      "module_tag": "one exact tag from the catalog or null",
      "target_files": ["exact filename from the catalog"]
    }}
  ]
}}

Rules:
- `unfocused` means broad chunk retrieval without extra narrowing.
- `focused` means chunk retrieval narrowed by an exact tag, exact files, or both.
- Keep `text` short and search-friendly for `unfocused` and `focused`.
- `module_tag` must be one exact tag from the catalog or null.
- `target_files` must contain only exact filenames from the catalog.
- Never invent tags or files outside the catalog.

Selected files: {selected_files_label}
Workspace catalog:
{json.dumps(workspace_catalog, ensure_ascii=True, sort_keys=True)}

User question: {message}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            plan = json.loads(response.text or "{}")
            normalized = self._normalize_query_plan(
                plan.get("queries"),
                workspace_catalog=workspace_catalog,
                fallback_message=message,
            )
            if normalized:
                return normalized
        except Exception as exc:
            logger.warning("Falling back to heuristic query plan: %s", exc)

        return self._fallback_query_plan(message, workspace_catalog)

    def _normalize_query_plan(
        self,
        items: Any,
        workspace_catalog: Dict[str, Any],
        fallback_message: str,
    ) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []

        available_tags = sorted((workspace_catalog.get("tags") or {}).keys())
        available_files = self._get_catalog_files(workspace_catalog)
        normalized: List[Dict[str, Any]] = []
        seen_steps = set()

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            module_tag = self._normalize_module_tag(item.get("module_tag"), available_tags)
            target_files = self._normalize_target_files(item.get("target_files"), available_files)
            search_mode = self._normalize_search_mode(item.get("search_mode"), module_tag, target_files)
            text = " ".join(str(item.get("text", "")).split())
            if not text:
                continue

            if search_mode == "unfocused":
                module_tag = None
                target_files = []
            elif search_mode == "focused" and not module_tag and not target_files:
                search_mode = "unfocused"

            dedupe_key = (
                search_mode,
                text.lower(),
                (module_tag or "").lower(),
                tuple(filename.lower() for filename in target_files),
            )
            if dedupe_key in seen_steps:
                continue
            seen_steps.add(dedupe_key)

            normalized.append(
                {
                    "query_id": f"q{len(normalized) + 1}",
                    "text": text,
                    "goal": " ".join(str(item.get("goal", "")).split()) or f"Explore angle {index + 1}",
                    "search_mode": search_mode,
                    "module_tag": module_tag,
                    "target_files": target_files,
                }
            )

            if len(normalized) == self.QUERY_COUNT:
                break

        if normalized:
            return normalized[: self.QUERY_COUNT]

        return self._fallback_query_plan(fallback_message, workspace_catalog)

    def _fallback_query_plan(
        self,
        message: str,
        workspace_catalog: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        base_message = message.strip() or "student study question"
        available_tags = sorted((workspace_catalog.get("tags") or {}).keys())
        available_files = self._get_catalog_files(workspace_catalog)
        inferred_tag = self._infer_module_tag(base_message, available_tags)
        inferred_files = self._infer_target_files(base_message, available_files)

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
                "search_mode": "focused" if inferred_tag else "unfocused",
                "module_tag": inferred_tag,
                "target_files": inferred_files if index == 0 else [],
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

    def _infer_target_files(self, message: str, available_files: List[str]) -> List[str]:
        lowered_message = message.lower()
        matched = [
            filename
            for filename in available_files
            if filename.lower() in lowered_message
        ]
        return matched[: self.FULL_DOCUMENT_FETCH_LIMIT]

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

    def _normalize_target_files(
        self,
        value: Any,
        available_files: List[str],
    ) -> List[str]:
        if not isinstance(value, list):
            return []

        allowed_lookup = {filename.lower(): filename for filename in available_files}
        normalized: List[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            match = allowed_lookup.get(item.strip().lower())
            if match and match not in normalized:
                normalized.append(match)
        return normalized

    def _normalize_search_mode(
        self,
        value: Any,
        module_tag: Optional[str],
        target_files: List[str],
    ) -> str:
        if isinstance(value, str):
            lowered = value.strip().lower().replace("-", "_").replace(" ", "_")
            if lowered in {"unfocused", "broad", "general"}:
                return "unfocused"
            if lowered in {"focused", "narrow", "filtered"}:
                return "focused"

        if target_files:
            return "focused"
        if module_tag:
            return "focused"
        return "unfocused"

    def _execute_search_plan(
        self,
        planned_queries: List[Dict[str, Any]],
        owner_username: str,
        selected_files: Optional[List[str]],
        workspace_catalog: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        available_tags = sorted((workspace_catalog.get("tags") or {}).keys())
        available_files = self._get_catalog_files(workspace_catalog)
        retrieval_runs: List[Dict[str, Any]] = []

        for item in planned_queries:
            module_tag = self._normalize_module_tag(item.get("module_tag"), available_tags)
            search_mode = self._normalize_search_mode(item.get("search_mode"), module_tag, item.get("target_files") or [])
            target_files = self._normalize_target_files(item.get("target_files"), available_files)

            active_files = target_files or selected_files
            active_tags = [module_tag] if module_tag else None
            if search_mode == "unfocused":
                active_files = selected_files
                active_tags = None

            raw_results = self.vector_store.search(
                item["text"],
                owner_username=owner_username,
                n_results=self.SEARCH_RESULTS_PER_QUERY,
                selected_files=active_files,
                selected_tags=active_tags,
            )

            retrieval_runs.append(
                {
                    "query_id": item["query_id"],
                    "query": item["text"],
                    "goal": item["goal"],
                    "search_mode": search_mode,
                    "module_tag": module_tag,
                    "target_files": target_files,
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

    def _build_source_summary(
        self,
        fused_results: List[Dict[str, Any]],
        full_document_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        chunk_sources = [
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
        return chunk_sources + list(full_document_sources or [])

    def _generate_response_with_document_fallback(
        self,
        message: str,
        owner_username: str,
        fused_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        answer_plan = self._assess_retrieved_evidence(message, fused_results)

        full_document_sources: List[Dict[str, Any]] = []
        full_document_fetches: List[Dict[str, Any]] = []

        requested_filenames = answer_plan.get("full_document_filenames") or []
        if answer_plan.get("needs_full_documents") and requested_filenames:
            for index, filename in enumerate(requested_filenames[: self.FULL_DOCUMENT_FETCH_LIMIT], start=1):
                document_payload = self.vector_store.get_full_document_content(owner_username, filename)
                if not document_payload or not (document_payload.get("content") or "").strip():
                    continue

                source_id = f"F{index}"
                full_document_sources.append(
                    {
                        "source_id": source_id,
                        "doc_id": None,
                        "filename": filename,
                        "chunk_index": None,
                        "distance": None,
                        "tag": document_payload.get("tag"),
                        "source_type": "full_document",
                    }
                )
                full_document_fetches.append(
                    {
                        "source_id": source_id,
                        "filename": filename,
                        "tag": document_payload.get("tag"),
                        "source": document_payload.get("source"),
                        "reason": answer_plan.get("missing_information"),
                    }
                )

        if full_document_sources:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=self._create_augmented_prompt(message, fused_results, full_document_sources, owner_username),
            )
            if not response.text:
                raise ValueError("Empty response from Gemini")
            return {
                "response": response.text,
                "full_document_sources": full_document_sources,
                "full_document_fetches": full_document_fetches,
            }

        if answer_plan.get("answer"):
            return {
                "response": answer_plan["answer"],
                "full_document_sources": [],
                "full_document_fetches": [],
            }

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=self._create_prompt(message, fused_results),
        )
        if not response.text:
            raise ValueError("Empty response from Gemini")
        return {
            "response": response.text,
            "full_document_sources": [],
            "full_document_fetches": [],
        }

    def _assess_retrieved_evidence(
        self,
        message: str,
        fused_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        evidence_context = self._build_evidence_context(fused_results)
        candidate_filenames = sorted(
            {
                item.get("filename")
                for item in fused_results
                if item.get("filename")
            }
        )

        prompt = f"""You are evaluating retrieval quality for a RAG answer.
Use the retrieved chunk evidence to draft the best answer you can.

Then decide whether the answer is still incomplete in a way that is likely resolvable by reading the full source document.

Return JSON with this exact shape:
{{
  "answer": "string",
  "needs_full_documents": true,
  "full_document_filenames": ["exact filename"],
  "missing_information": "short reason"
}}

Rules:
- `full_document_filenames` must contain only exact filenames from the allowed list.
- Request full documents only when the current chunks are insufficient and the missing details are likely in the same source document.
- Prefer at most {self.FULL_DOCUMENT_FETCH_LIMIT} filenames.
- If the current chunks are enough, set `needs_full_documents` to false and `full_document_filenames` to [].

Allowed filenames: {", ".join(candidate_filenames) or "None"}

Retrieved evidence:
{evidence_context or "None"}

User question:
{message}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            payload = json.loads(response.text or "{}")
            return self._normalize_answer_plan(payload, candidate_filenames)
        except Exception as exc:
            logger.warning("Falling back to direct answer generation: %s", exc)
            return {
                "answer": "",
                "needs_full_documents": False,
                "full_document_filenames": [],
                "missing_information": "",
            }

    def _normalize_answer_plan(
        self,
        payload: Any,
        candidate_filenames: List[str],
    ) -> Dict[str, Any]:
        normalized = {
            "answer": "",
            "needs_full_documents": False,
            "full_document_filenames": [],
            "missing_information": "",
        }
        if not isinstance(payload, dict):
            return normalized

        answer = payload.get("answer")
        if isinstance(answer, str):
            normalized["answer"] = answer.strip()

        missing_information = payload.get("missing_information")
        if isinstance(missing_information, str):
            normalized["missing_information"] = missing_information.strip()

        allowed_lookup = {filename.lower(): filename for filename in candidate_filenames}
        requested_files: List[str] = []
        for item in payload.get("full_document_filenames") or []:
            if not isinstance(item, str):
                continue
            match = allowed_lookup.get(item.strip().lower())
            if match and match not in requested_files:
                requested_files.append(match)

        normalized["full_document_filenames"] = requested_files[: self.FULL_DOCUMENT_FETCH_LIMIT]
        normalized["needs_full_documents"] = bool(payload.get("needs_full_documents")) and bool(requested_files)
        return normalized

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

    def _create_augmented_prompt(
        self,
        message: str,
        fused_results: List[Dict[str, Any]],
        full_document_sources: List[Dict[str, Any]],
        owner_username: str,
    ) -> str:
        chunk_evidence = self._build_evidence_context(fused_results)

        document_parts = []
        for source in full_document_sources:
            filename = source.get("filename")
            if not filename:
                continue
            document_payload = self.vector_store.get_full_document_content(owner_username, filename)
            if not document_payload:
                continue

            header_bits = [source["source_id"], filename, "full document"]
            if source.get("tag"):
                header_bits.append(f"module {source['tag']}")
            document_parts.append(
                f"[{' | '.join(header_bits)}]\n{(document_payload.get('content') or '').strip()}"
            )

        full_document_context = "\n\n".join(document_parts)

        return f"""You are a helpful AI assistant for students studying academic modules.
Answer the user's question using the retrieved chunk evidence and the full-document context.

Rules:
- Use the full-document context when it fills gaps left by the retrieved chunks.
- Cite chunk evidence ids inline like [S1].
- Cite full-document evidence ids inline like [F1].
- If information is still missing, say so clearly.
- Keep the answer clear, concise, and useful.

Retrieved chunk evidence:
{chunk_evidence or "None"}

Full-document context:
{full_document_context or "None"}

User question:
{message}
"""

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
