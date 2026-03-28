"""
Utilities for building a token-light catalog of the general RAG workspace.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_workspace_catalog(owner_username: str, database: Any, vector_store: Any) -> Dict[str, Any]:
    """
    Build a compact catalog for the general study workspace only.

    The payload is intentionally minimal because it is designed to be sent to
    the LLM planner. It is always localized to the requesting user because the
    searchable document list is fetched through the user-scoped vector-store API.
    """
    del database
    return build_workspace_catalog_snapshot(
        searchable_documents=vector_store.list_documents(owner_username),
    )


def build_workspace_catalog_snapshot(
    searchable_documents: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    normalized_documents = _normalize_documents(searchable_documents or [])

    tags: Dict[str, List[str]] = {}
    untagged_files: List[str] = []

    for document in normalized_documents:
        filename = document["filename"]
        tag = document.get("tag")
        if tag:
            tags.setdefault(tag, []).append(filename)
        else:
            untagged_files.append(filename)

    catalog: Dict[str, Any] = {"tags": tags}
    if untagged_files:
        catalog["untagged_files"] = untagged_files

    return catalog


def _normalize_documents(searchable_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen_filenames = set()

    for raw_document in searchable_documents:
        if not isinstance(raw_document, dict):
            continue

        filename = _normalize_text(raw_document.get("filename"))
        if not filename or filename in seen_filenames:
            continue
        seen_filenames.add(filename)

        normalized.append(
            {
                "filename": filename,
                "tag": _normalize_tag(raw_document.get("tag")),
            }
        )

    return sorted(normalized, key=lambda item: item["filename"].lower())


def _normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    normalized = " ".join(value.split()).strip()
    return normalized or None


def _normalize_tag(value: Any) -> Optional[str]:
    normalized = _normalize_text(value)
    if not normalized or normalized.lower() == "uncategorized":
        return None
    return normalized
