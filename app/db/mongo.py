from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError


class MongoDatabase:
    def __init__(self, client: MongoClient, db_name: str):
        self.client = client
        self.database: Database = client[db_name]
        self.users: Collection = self.database["users"]
        self.sessions: Collection = self.database["sessions"]
        self.tags: Collection = self.database["tags"]
        self.notes: Collection = self.database["notes"]
        self.folders: Collection = self.database["folders"]
        self.documents: Collection = self.database["documents"]
        self.exam_folder_analyses: Collection = self.database["exam_folder_analyses"]
        self.exam_documents: Collection = self.database["exam_documents"]

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _iso(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
            return value.isoformat()
        return str(value)

    @staticmethod
    def _coerce_datetime(value: Any) -> Any:
        if isinstance(value, datetime) or value is None:
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @staticmethod
    def _name_key(name: str) -> str:
        return " ".join(name.split()).strip().lower()

    @staticmethod
    def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "created_at": MongoDatabase._iso(user.get("created_at")),
        }

    @staticmethod
    def _serialize_folder(folder: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": folder.get("id"),
            "name": folder.get("name"),
            "created_at": MongoDatabase._iso(folder.get("created_at")),
        }

    @staticmethod
    def _serialize_note(note: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": note.get("id"),
            "content": note.get("content"),
            "created_at": MongoDatabase._iso(note.get("created_at")),
        }

    @staticmethod
    def _serialize_exam_document(document: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(document)
        payload.pop("_id", None)
        payload["created_at"] = MongoDatabase._iso(payload.get("created_at"))
        return payload

    @staticmethod
    def _analysis_summary(analysis: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(analysis, dict):
            return None

        raw_summary = analysis.get("summary")
        summary = dict(raw_summary) if isinstance(raw_summary, dict) else {}
        return {
            "status": analysis.get("status"),
            "stage": analysis.get("stage"),
            "progress": analysis.get("progress"),
            "updated_at": MongoDatabase._iso(analysis.get("updated_at")),
            "completed_at": MongoDatabase._iso(analysis.get("completed_at")),
            "error": analysis.get("error"),
            "stale": bool(analysis.get("stale")),
            "job_id": analysis.get("job_id"),
            "model": analysis.get("model"),
            "pipeline_version": analysis.get("pipeline_version"),
            "summary": summary,
        }

    def ping(self) -> None:
        self.client.admin.command("ping")

    def ensure_indexes(self) -> None:
        self.users.create_index([("username", ASCENDING)], unique=True)
        self.sessions.create_index([("id", ASCENDING)], unique=True)
        self.sessions.create_index([("user_id", ASCENDING)])
        self.sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
        self.tags.create_index([("user_id", ASCENDING), ("tag", ASCENDING)], unique=True)
        self.notes.create_index([("id", ASCENDING)], unique=True)
        self.notes.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        self.folders.create_index(
            [("user_id", ASCENDING), ("kind", ASCENDING), ("name_key", ASCENDING)],
            unique=True,
        )
        self.documents.create_index([("user_id", ASCENDING), ("filename", ASCENDING)], unique=True)
        self.exam_folder_analyses.create_index([("user_id", ASCENDING), ("folder_id", ASCENDING)], unique=True)
        self.exam_documents.create_index([("id", ASCENDING)], unique=True)
        self.exam_documents.create_index([("user_id", ASCENDING), ("folder_id", ASCENDING)])

    def _get_user_record(self, username: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"username": username}, {"_id": 0})

    def _require_user_record(self, username: str) -> Dict[str, Any]:
        user = self._get_user_record(username)
        if not user:
            raise ValueError("User not found")
        return user

    def _mark_exam_folder_analysis_stale(self, user_id: str, folder_ids: List[Optional[str]]) -> None:
        filtered_ids = [folder_id for folder_id in folder_ids if folder_id]
        if not filtered_ids:
            return

        self.exam_folder_analyses.update_many(
            {"user_id": user_id, "folder_id": {"$in": filtered_ids}},
            {"$set": {"stale": True, "updated_at": self._now()}},
        )

    def create_user(self, username: str, password_hash: str, password_salt: str) -> Dict[str, Any]:
        if self._get_user_record(username):
            raise ValueError("Username already exists")

        now = self._now()
        user = {
            "id": uuid.uuid4().hex,
            "username": username,
            "password_hash": password_hash,
            "password_salt": password_salt,
            "created_at": now,
        }
        try:
            self.users.insert_one(user)
        except DuplicateKeyError as exc:
            raise ValueError("Username already exists") from exc
        return self._public_user(user)

    def get_user_credentials(self, username: str) -> Optional[Dict[str, str]]:
        user = self._get_user_record(username)
        if not user:
            return None
        return {
            "password_hash": user.get("password_hash", ""),
            "password_salt": user.get("password_salt", ""),
        }

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        return self._public_user(user) if user else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.get_user(username)

    def get_raw_user(self, username: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return None

        user_id = user["id"]
        study_folders = self.folders.find({"user_id": user_id, "kind": "study"}, {"_id": 0}).sort("name_key", ASCENDING)
        exam_folders = self.folders.find({"user_id": user_id, "kind": "exam"}, {"_id": 0}).sort("name_key", ASCENDING)
        notes = self.notes.find({"user_id": user_id}, {"_id": 0}).sort("created_at", ASCENDING)
        tags = self.tags.find({"user_id": user_id}, {"_id": 0, "tag": 1}).sort("tag", ASCENDING)
        sessions = self.sessions.find({"user_id": user_id}, {"_id": 0}).sort("created_at", ASCENDING)
        analyses = self.exam_folder_analyses.find({"user_id": user_id}, {"_id": 0})
        exam_documents = self.exam_documents.find({"user_id": user_id}, {"_id": 0}).sort(
            [("folder_name", ASCENDING), ("filename", ASCENDING)]
        )
        documents = self.documents.find({"user_id": user_id}, {"_id": 0, "filename": 1, "metadata": 1})

        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "password_hash": user.get("password_hash", ""),
            "password_salt": user.get("password_salt", ""),
            "created_at": self._iso(user.get("created_at")),
            "tags": [item.get("tag") for item in tags if item.get("tag")],
            "notes": [self._serialize_note(note) for note in notes],
            "folders": [self._serialize_folder(folder) for folder in study_folders],
            "exam_folders": [self._serialize_folder(folder) for folder in exam_folders],
            "exam_folder_analyses": {
                analysis["folder_id"]: {
                    **analysis,
                    "created_at": self._iso(analysis.get("created_at")),
                    "updated_at": self._iso(analysis.get("updated_at")),
                    "completed_at": self._iso(analysis.get("completed_at")),
                }
                for analysis in analyses
                if analysis.get("folder_id")
            },
            "exam_documents": {
                document["id"]: self._serialize_exam_document(document)
                for document in exam_documents
                if document.get("id")
            },
            "documents": {
                record["filename"]: dict(record.get("metadata", {}))
                for record in documents
                if record.get("filename")
            },
            "sessions": [
                {
                    "id": session.get("id"),
                    "hash": session.get("hash"),
                    "created_at": self._iso(session.get("created_at")),
                    "expires_at": self._iso(session.get("expires_at")),
                }
                for session in sessions
            ],
        }

    def create_session(self, username: str, session_id: str, session_hash: str, expires_at: str) -> Dict[str, Any]:
        user = self._require_user_record(username)
        session = {
            "id": session_id,
            "user_id": user["id"],
            "username": username,
            "hash": session_hash,
            "created_at": self._now(),
            "expires_at": datetime.fromisoformat(expires_at),
        }
        self.sessions.insert_one(session)
        return {
            "id": session["id"],
            "hash": session["hash"],
            "created_at": self._iso(session["created_at"]),
            "expires_at": self._iso(session["expires_at"]),
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            return None
        return {
            "username": session.get("username"),
            "id": session.get("id"),
            "hash": session.get("hash"),
            "created_at": self._iso(session.get("created_at")),
            "expires_at": self._iso(session.get("expires_at")),
        }

    def delete_session(self, session_id: str) -> bool:
        result = self.sessions.delete_one({"id": session_id})
        return result.deleted_count > 0

    def delete_user(self, username: str) -> bool:
        user = self._get_user_record(username)
        if not user:
            return False

        user_id = user["id"]
        self.sessions.delete_many({"user_id": user_id})
        self.tags.delete_many({"user_id": user_id})
        self.notes.delete_many({"user_id": user_id})
        self.folders.delete_many({"user_id": user_id})
        self.documents.delete_many({"user_id": user_id})
        self.exam_folder_analyses.delete_many({"user_id": user_id})
        self.exam_documents.delete_many({"user_id": user_id})
        result = self.users.delete_one({"id": user_id})
        return result.deleted_count > 0

    def get_tags(self, username: str) -> List[str]:
        user = self._get_user_record(username)
        if not user:
            return []
        docs = self.tags.find({"user_id": user["id"]}, {"_id": 0, "tag": 1}).sort("tag", ASCENDING)
        return [item["tag"] for item in docs]

    def add_tag(self, username: str, tag: str) -> bool:
        user = self._get_user_record(username)
        if not user:
            return False
        result = self.tags.update_one(
            {"user_id": user["id"], "tag": tag},
            {"$setOnInsert": {"created_at": self._now()}},
            upsert=True,
        )
        return bool(result.upserted_id)

    def delete_tag(self, username: str, tag: str) -> bool:
        user = self._get_user_record(username)
        if not user:
            return False
        result = self.tags.delete_one({"user_id": user["id"], "tag": tag})
        return result.deleted_count > 0

    def get_notes(self, username: str) -> List[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return []
        notes = self.notes.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", ASCENDING)
        return [self._serialize_note(note) for note in notes]

    def list_folders(self, username: str) -> List[Dict[str, Any]]:
        return self._list_folders_by_kind(username, "study")

    def _list_folders_by_kind(self, username: str, kind: str) -> List[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return []
        folders = self.folders.find({"user_id": user["id"], "kind": kind}, {"_id": 0}).sort("name_key", ASCENDING)
        return [self._serialize_folder(folder) for folder in folders]

    def get_folder(self, username: str, folder_id: str) -> Optional[Dict[str, Any]]:
        return self._get_folder_by_kind(username, folder_id, "study")

    def _get_folder_by_kind(self, username: str, folder_id: str, kind: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return None
        folder = self.folders.find_one({"user_id": user["id"], "kind": kind, "id": folder_id}, {"_id": 0})
        return self._serialize_folder(folder) if folder else None

    def create_folder(self, username: str, name: str) -> Dict[str, Any]:
        return self._create_folder_by_kind(username, name, "study")

    def _create_folder_by_kind(self, username: str, name: str, kind: str) -> Dict[str, Any]:
        normalized_name = " ".join(name.split()).strip()
        if not normalized_name:
            raise ValueError("Folder name is required")

        user = self._require_user_record(username)
        name_key = self._name_key(normalized_name)
        existing = self.folders.find_one({"user_id": user["id"], "kind": kind, "name_key": name_key}, {"_id": 1})
        if existing:
            raise ValueError("Folder already exists")

        folder = {
            "id": uuid.uuid4().hex,
            "user_id": user["id"],
            "kind": kind,
            "name": normalized_name,
            "name_key": name_key,
            "created_at": self._now(),
        }
        try:
            self.folders.insert_one(folder)
        except DuplicateKeyError as exc:
            raise ValueError("Folder already exists") from exc
        return self._serialize_folder(folder)

    def list_exam_folders(self, username: str) -> List[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return []

        folders = self.folders.find({"user_id": user["id"], "kind": "exam"}, {"_id": 0}).sort("name_key", ASCENDING)
        payload: List[Dict[str, Any]] = []
        for folder in folders:
            serialized = self._serialize_folder(folder)
            analysis = self.exam_folder_analyses.find_one(
                {"user_id": user["id"], "folder_id": folder["id"]},
                {"_id": 0},
            )
            serialized["analysis"] = self._analysis_summary(analysis)
            payload.append(serialized)
        return payload

    def get_exam_folder(self, username: str, folder_id: str) -> Optional[Dict[str, Any]]:
        return self._get_folder_by_kind(username, folder_id, "exam")

    def create_exam_folder(self, username: str, name: str) -> Dict[str, Any]:
        return self._create_folder_by_kind(username, name, "exam")

    def get_exam_folder_analysis(self, username: str, folder_id: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return None
        analysis = self.exam_folder_analyses.find_one({"user_id": user["id"], "folder_id": folder_id}, {"_id": 0})
        if not analysis:
            return None
        analysis["created_at"] = self._iso(analysis.get("created_at"))
        analysis["updated_at"] = self._iso(analysis.get("updated_at"))
        analysis["completed_at"] = self._iso(analysis.get("completed_at"))
        return analysis

    def save_exam_folder_analysis(self, username: str, folder_id: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        user = self._require_user_record(username)
        next_analysis = dict(analysis)
        next_analysis["user_id"] = user["id"]
        next_analysis["folder_id"] = folder_id
        next_analysis["created_at"] = self._coerce_datetime(next_analysis["created_at"])
        if next_analysis.get("updated_at"):
            next_analysis["updated_at"] = self._coerce_datetime(next_analysis["updated_at"])
        if next_analysis.get("completed_at"):
            next_analysis["completed_at"] = self._coerce_datetime(next_analysis["completed_at"])
        self.exam_folder_analyses.replace_one(
            {"user_id": user["id"], "folder_id": folder_id},
            next_analysis,
            upsert=True,
        )
        return self.get_exam_folder_analysis(username, folder_id) or {}

    def update_exam_folder_analysis(self, username: str, folder_id: str, **updates: Any) -> Dict[str, Any]:
        user = self._require_user_record(username)
        current = self.exam_folder_analyses.find_one({"user_id": user["id"], "folder_id": folder_id}, {"_id": 0})
        now = self._now()
        if not isinstance(current, dict):
            current = {
                "user_id": user["id"],
                "folder_id": folder_id,
                "status": "idle",
                "stage": "",
                "progress": 0,
                "summary": {},
                "result": None,
                "error": None,
                "stale": False,
                "created_at": now,
            }
        next_analysis = dict(current)
        next_analysis.update(updates)
        next_analysis["updated_at"] = now
        self.exam_folder_analyses.replace_one(
            {"user_id": user["id"], "folder_id": folder_id},
            next_analysis,
            upsert=True,
        )
        return self.get_exam_folder_analysis(username, folder_id) or {}

    def add_note(self, username: str, content: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return None
        note = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "content": content,
            "created_at": self._now(),
        }
        self.notes.insert_one(note)
        return self._serialize_note(note)

    def delete_note(self, username: str, note_id: str) -> bool:
        user = self._get_user_record(username)
        if not user:
            return False
        result = self.notes.delete_one({"user_id": user["id"], "id": note_id})
        return result.deleted_count > 0

    def set_document_metadata(self, username: str, filename: str, metadata: Dict[str, Any]) -> None:
        user = self._get_user_record(username)
        if not user:
            return
        existing = self.documents.find_one({"user_id": user["id"], "filename": filename}, {"_id": 0, "metadata": 1})
        next_metadata = dict(existing.get("metadata", {})) if existing else {}
        next_metadata.update(metadata)
        self.documents.update_one(
            {"user_id": user["id"], "filename": filename},
            {
                "$set": {
                    "metadata": next_metadata,
                    "updated_at": self._now(),
                },
                "$setOnInsert": {
                    "user_id": user["id"],
                    "filename": filename,
                    "created_at": self._now(),
                },
            },
            upsert=True,
        )

    def get_document_metadata(self, username: str, filename: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return None
        existing = self.documents.find_one({"user_id": user["id"], "filename": filename}, {"_id": 0, "metadata": 1})
        if not existing:
            return None
        metadata = existing.get("metadata")
        return dict(metadata) if isinstance(metadata, dict) else {}

    def set_document_folder(self, username: str, filename: str, folder_id: Optional[str]) -> Dict[str, Any]:
        user = self._require_user_record(username)

        folder_name = None
        normalized_folder_id = folder_id or None
        if normalized_folder_id:
            folder = self.folders.find_one(
                {"user_id": user["id"], "kind": "study", "id": normalized_folder_id},
                {"_id": 0, "name": 1},
            )
            if not folder:
                raise ValueError("Folder not found")
            folder_name = folder.get("name")

        existing = self.documents.find_one({"user_id": user["id"], "filename": filename}, {"_id": 0, "metadata": 1})
        next_metadata = dict(existing.get("metadata", {})) if existing else {}
        next_metadata["folder_id"] = normalized_folder_id
        next_metadata["folder_name"] = folder_name
        self.documents.update_one(
            {"user_id": user["id"], "filename": filename},
            {
                "$set": {"metadata": next_metadata, "updated_at": self._now()},
                "$setOnInsert": {
                    "user_id": user["id"],
                    "filename": filename,
                    "created_at": self._now(),
                },
            },
            upsert=True,
        )
        return dict(next_metadata)

    def list_exam_documents(self, username: str) -> List[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return []
        documents = self.exam_documents.find({"user_id": user["id"]}, {"_id": 0}).sort(
            [("folder_name", ASCENDING), ("filename", ASCENDING)]
        )
        return [self._serialize_exam_document(document) for document in documents]

    def add_exam_document(self, username: str, document: Dict[str, Any]) -> Dict[str, Any]:
        user = self._require_user_record(username)
        doc_id = document.get("id") or uuid.uuid4().hex
        next_document = dict(document)
        next_document["id"] = doc_id
        next_document["user_id"] = user["id"]
        next_document["created_at"] = datetime.fromisoformat(next_document["created_at"])
        self.exam_documents.replace_one(
            {"id": doc_id},
            next_document,
            upsert=True,
        )
        self._mark_exam_folder_analysis_stale(user["id"], [next_document.get("folder_id")])
        return self.get_exam_document(username, doc_id) or {}

    def get_exam_document(self, username: str, document_id: str) -> Optional[Dict[str, Any]]:
        user = self._get_user_record(username)
        if not user:
            return None
        document = self.exam_documents.find_one({"user_id": user["id"], "id": document_id}, {"_id": 0})
        return self._serialize_exam_document(document) if document else None

    def update_exam_document_folder(self, username: str, document_id: str, folder_id: str) -> Dict[str, Any]:
        user = self._require_user_record(username)
        document = self.exam_documents.find_one({"user_id": user["id"], "id": document_id})
        if not isinstance(document, dict):
            raise ValueError("Exam document not found")

        folder = self.folders.find_one({"user_id": user["id"], "kind": "exam", "id": folder_id}, {"_id": 0})
        if not folder:
            raise ValueError("Folder not found")

        previous_folder_id = document.get("folder_id")
        self.exam_documents.update_one(
            {"user_id": user["id"], "id": document_id},
            {"$set": {"folder_id": folder["id"], "folder_name": folder["name"]}},
        )
        self._mark_exam_folder_analysis_stale(user["id"], [previous_folder_id, folder["id"]])
        return self.get_exam_document(username, document_id) or {}

    def delete_document_metadata(self, username: str, filename: str) -> bool:
        user = self._get_user_record(username)
        if not user:
            return False
        result = self.documents.delete_one({"user_id": user["id"], "filename": filename})
        return result.deleted_count > 0

    def get_all_metadata(self, username: str) -> Dict[str, Any]:
        user = self._get_user_record(username)
        if not user:
            return {}
        records = self.documents.find({"user_id": user["id"]}, {"_id": 0, "filename": 1, "metadata": 1})
        return {record["filename"]: dict(record.get("metadata", {})) for record in records}
