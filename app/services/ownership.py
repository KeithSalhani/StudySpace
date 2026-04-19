from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.db.repository import DatabaseRepository
from app.db.vector_store import VectorStore


def get_owned_document_metadata(
    database: DatabaseRepository,
    vector_store: VectorStore,
    owner_username: str,
    filename: str,
) -> Dict[str, Any]:
    metadata = vector_store.get_document_metadata(owner_username, filename)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    return metadata


def get_owned_folder(database: DatabaseRepository, owner_username: str, folder_id: str) -> Dict[str, Any]:
    folder = database.get_folder(owner_username, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


def get_owned_exam_folder(database: DatabaseRepository, owner_username: str, folder_id: str) -> Dict[str, Any]:
    folder = database.get_exam_folder(owner_username, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Exam folder not found")
    return folder


def get_owned_exam_document(
    database: DatabaseRepository,
    owner_username: str,
    document_id: str,
) -> Dict[str, Any]:
    document = database.get_exam_document(owner_username, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    return document


def list_exam_folder_documents(
    database: DatabaseRepository,
    owner_username: str,
    folder_id: str,
) -> List[Dict[str, Any]]:
    return [
        document
        for document in database.list_exam_documents(owner_username)
        if document.get("folder_id") == folder_id
    ]


def ensure_selected_files_owned(
    vector_store: VectorStore,
    owner_username: str,
    selected_files: Optional[List[str]],
) -> Optional[List[str]]:
    if not selected_files:
        return None

    owned_files: List[str] = []
    for filename in selected_files:
        if not vector_store.get_document_metadata(owner_username, filename):
            raise HTTPException(status_code=404, detail=f"Document not found: {filename}")
        owned_files.append(filename)
    return owned_files
