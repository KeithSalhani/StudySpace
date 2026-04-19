from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from app.db.repository import DatabaseRepository
from app.db.vector_store import VectorStore
from app.services.frontend import get_frontend_asset_version
from app.services.storage import user_root


def scrub_user_export_payload(raw_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(raw_user, dict):
        return {}

    payload = dict(raw_user)
    payload.pop("password_hash", None)
    payload.pop("password_salt", None)

    sessions = []
    for session in payload.get("sessions", []):
        if not isinstance(session, dict):
            continue
        sessions.append(
            {
                "id": session.get("id"),
                "created_at": session.get("created_at"),
                "expires_at": session.get("expires_at"),
            }
        )
    payload["sessions"] = sessions
    return payload


def write_json_to_zip(archive: ZipFile, archive_path: str, payload: Any) -> None:
    archive.writestr(
        archive_path,
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
    )


def add_directory_to_zip(archive: ZipFile, root_path: Path, archive_root: str) -> None:
    if not root_path.exists() or not root_path.is_dir():
        return

    for path in sorted(root_path.rglob("*")):
        if path.is_file():
            relative_path = path.relative_to(root_path).as_posix()
            archive.write(path, arcname=f"{archive_root}/{relative_path}")


def build_account_export(
    database: DatabaseRepository,
    vector_store: VectorStore,
    username: str,
) -> bytes:
    raw_user = database.get_raw_user(username)
    if not raw_user:
        raise HTTPException(status_code=404, detail="User not found")

    export_buffer = BytesIO()
    export_time = datetime.now(timezone.utc)
    scrubbed_user = scrub_user_export_payload(raw_user)
    root = user_root(username)

    with ZipFile(export_buffer, "w", compression=ZIP_DEFLATED) as archive:
        write_json_to_zip(
            archive,
            "manifest.json",
            {
                "app": "Study Space",
                "exported_at": export_time.isoformat(),
                "username": username,
                "version": get_frontend_asset_version(),
            },
        )
        write_json_to_zip(
            archive,
            "account/profile.json",
            {
                "id": scrubbed_user.get("id"),
                "username": scrubbed_user.get("username"),
                "created_at": scrubbed_user.get("created_at"),
            },
        )
        write_json_to_zip(archive, "account/sessions.json", scrubbed_user.get("sessions", []))
        write_json_to_zip(archive, "workspace/tags.json", scrubbed_user.get("tags", []))
        write_json_to_zip(archive, "workspace/notes.json", scrubbed_user.get("notes", []))
        write_json_to_zip(archive, "workspace/folders.json", scrubbed_user.get("folders", []))
        write_json_to_zip(archive, "workspace/exam_folders.json", scrubbed_user.get("exam_folders", []))
        write_json_to_zip(
            archive,
            "workspace/exam_folder_analyses.json",
            scrubbed_user.get("exam_folder_analyses", {}),
        )
        write_json_to_zip(archive, "workspace/document_metadata.json", scrubbed_user.get("documents", {}))
        write_json_to_zip(archive, "workspace/exam_documents.json", scrubbed_user.get("exam_documents", {}))
        write_json_to_zip(archive, "workspace/study_sets.json", scrubbed_user.get("study_sets", []))
        write_json_to_zip(
            archive,
            "workspace/vector_documents.json",
            vector_store.list_all_document_metadata(username),
        )

        add_directory_to_zip(archive, root / "uploads", "documents/uploads")
        add_directory_to_zip(archive, root / "processed", "documents/processed")
        add_directory_to_zip(archive, root / "exam_papers", "documents/exam_papers")

    export_buffer.seek(0)
    return export_buffer.getvalue()


def delete_account_data(
    database: DatabaseRepository,
    vector_store: VectorStore,
    username: str,
) -> None:
    root = user_root(username)

    vector_store.delete_user_documents(username)
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)

    deleted = database.delete_user(username)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
