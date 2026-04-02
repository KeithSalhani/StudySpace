#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from pymongo import MongoClient

from app.db.mongo import MongoDatabase


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Legacy JSON database must contain a top-level object")
    users = payload.get("users", {})
    if not isinstance(users, dict):
        raise ValueError("Legacy JSON database is missing a valid 'users' object")
    return users


def _name_key(name: str) -> str:
    return " ".join(name.split()).strip().lower()


def _maybe_datetime(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return value


def _print(message: str) -> None:
    print(message, flush=True)


def migrate(json_path: Path, mongo_uri: str, db_name: str, dry_run: bool) -> None:
    users_payload = _load_json(json_path)

    client = MongoClient(mongo_uri)
    database = MongoDatabase(client, db_name)
    database.ping()
    database.ensure_indexes()

    user_count = 0
    session_count = 0
    tag_count = 0
    note_count = 0
    folder_count = 0
    document_count = 0
    analysis_count = 0
    exam_document_count = 0

    for username, raw_user in users_payload.items():
        if not isinstance(raw_user, dict):
            continue

        legacy_user_id = raw_user.get("id")
        if not isinstance(legacy_user_id, str) or not legacy_user_id:
            continue

        user_count += 1

        user_id = legacy_user_id
        if dry_run:
            existing_user = None
        else:
            existing_user = database.users.find_one({"username": username}, {"_id": 0, "id": 1})
            existing_user_id = existing_user.get("id") if isinstance(existing_user, dict) else None
            if isinstance(existing_user_id, str) and existing_user_id:
                user_id = existing_user_id

            database.users.update_one(
                {"username": username},
                {
                    "$set": {
                        "username": username,
                        "password_hash": raw_user.get("password_hash", ""),
                        "password_salt": raw_user.get("password_salt", ""),
                    },
                    "$setOnInsert": {
                        "id": user_id,
                        "created_at": _maybe_datetime(raw_user.get("created_at")),
                    },
                },
                upsert=True,
            )

        for session in raw_user.get("sessions", []):
            if not isinstance(session, dict) or not session.get("id"):
                continue
            session_count += 1
            if not dry_run:
                database.sessions.replace_one(
                    {"id": session["id"]},
                    {
                        "id": session["id"],
                        "user_id": user_id,
                        "username": username,
                        "hash": session.get("hash", ""),
                        "created_at": _maybe_datetime(session.get("created_at")),
                        "expires_at": _maybe_datetime(session.get("expires_at")),
                    },
                    upsert=True,
                )

        for tag in raw_user.get("tags", []):
            if not isinstance(tag, str) or not tag:
                continue
            tag_count += 1
            if not dry_run:
                database.tags.update_one(
                    {"user_id": user_id, "tag": tag},
                    {"$setOnInsert": {"created_at": raw_user.get("created_at")}},
                    upsert=True,
                )

        for note in raw_user.get("notes", []):
            if not isinstance(note, dict) or not note.get("id"):
                continue
            note_count += 1
            if not dry_run:
                database.notes.replace_one(
                    {"id": note["id"]},
                        {
                            "id": note["id"],
                            "user_id": user_id,
                            "content": note.get("content", ""),
                            "created_at": _maybe_datetime(note.get("created_at")),
                        },
                        upsert=True,
                    )

        for kind, source_key in (("study", "folders"), ("exam", "exam_folders")):
            for folder in raw_user.get(source_key, []):
                if not isinstance(folder, dict) or not folder.get("id") or not folder.get("name"):
                    continue
                folder_count += 1
                if not dry_run:
                    database.folders.replace_one(
                        {"user_id": user_id, "kind": kind, "id": folder["id"]},
                        {
                            "id": folder["id"],
                            "user_id": user_id,
                            "kind": kind,
                            "name": folder["name"],
                            "name_key": _name_key(folder["name"]),
                            "created_at": _maybe_datetime(folder.get("created_at")),
                        },
                        upsert=True,
                    )

        for filename, metadata in raw_user.get("documents", {}).items():
            if not isinstance(filename, str) or not isinstance(metadata, dict):
                continue
            document_count += 1
            if not dry_run:
                database.documents.replace_one(
                    {"user_id": user_id, "filename": filename},
                    {
                        "user_id": user_id,
                        "filename": filename,
                        "metadata": metadata,
                        "created_at": _maybe_datetime(metadata.get("created_at") or raw_user.get("created_at")),
                        "updated_at": _maybe_datetime(metadata.get("updated_at") or raw_user.get("created_at")),
                    },
                    upsert=True,
                )

        for folder_id, analysis in raw_user.get("exam_folder_analyses", {}).items():
            if not isinstance(folder_id, str) or not isinstance(analysis, dict):
                continue
            analysis_count += 1
            if not dry_run:
                next_analysis = dict(analysis)
                next_analysis["user_id"] = user_id
                next_analysis["folder_id"] = folder_id
                next_analysis["created_at"] = _maybe_datetime(next_analysis.get("created_at"))
                next_analysis["updated_at"] = _maybe_datetime(next_analysis.get("updated_at"))
                next_analysis["completed_at"] = _maybe_datetime(next_analysis.get("completed_at"))
                database.exam_folder_analyses.replace_one(
                    {"user_id": user_id, "folder_id": folder_id},
                    next_analysis,
                    upsert=True,
                )

        for document_id, document in raw_user.get("exam_documents", {}).items():
            if not isinstance(document_id, str) or not isinstance(document, dict):
                continue
            exam_document_count += 1
            if not dry_run:
                next_document = dict(document)
                next_document["id"] = next_document.get("id") or document_id
                next_document["user_id"] = user_id
                next_document["created_at"] = _maybe_datetime(next_document.get("created_at"))
                database.exam_documents.replace_one(
                    {"id": next_document["id"]},
                    next_document,
                    upsert=True,
                )

    _print(f"Users: {user_count}")
    _print(f"Sessions: {session_count}")
    _print(f"Tags: {tag_count}")
    _print(f"Notes: {note_count}")
    _print(f"Folders: {folder_count}")
    _print(f"Documents: {document_count}")
    _print(f"Exam folder analyses: {analysis_count}")
    _print(f"Exam documents: {exam_document_count}")
    _print("Dry run complete" if dry_run else "Migration complete")

    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy db.json data into MongoDB.")
    parser.add_argument("--json-path", required=True, help="Path to the legacy db.json file")
    parser.add_argument("--mongo-uri", required=True, help="MongoDB connection URI")
    parser.add_argument("--db-name", required=True, help="Target MongoDB database name")
    parser.add_argument("--dry-run", action="store_true", help="Read and count records without writing to MongoDB")
    args = parser.parse_args()

    migrate(
        json_path=Path(args.json_path),
        mongo_uri=args.mongo_uri,
        db_name=args.db_name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
