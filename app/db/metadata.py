import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class JSONDatabase:
    def __init__(self, db_path: str = "db.json"):
        self._lock = threading.RLock()
        self.db_path = db_path
        self.data = self._default_data()
        self.load()

    @staticmethod
    def _default_data() -> Dict[str, Any]:
        return {"users": {}}

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_or_create_user_unlocked(self, username: str) -> Dict[str, Any]:
        users = self.data.setdefault("users", {})
        if username not in users:
            users[username] = {
                "id": uuid.uuid4().hex,
                "username": username,
                "password_hash": "",
                "password_salt": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tags": [],
                "notes": [],
                "folders": [],
                "exam_folders": [],
                "exam_folder_analyses": {},
                "exam_documents": {},
                "documents": {},
                "sessions": [],
            }
        return users[username]

    def _migrate(self, loaded: Any) -> Dict[str, Any]:
        migrated = self._default_data()
        if not isinstance(loaded, dict):
            return migrated

        if isinstance(loaded.get("users"), dict):
            migrated["users"] = loaded["users"]
            for username, user in list(migrated["users"].items()):
                if not isinstance(user, dict):
                    migrated["users"].pop(username, None)
                    continue
                user.setdefault("id", uuid.uuid4().hex)
                user.setdefault("username", username)
                user.setdefault("password_hash", "")
                user.setdefault("password_salt", "")
                user.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                user.setdefault("tags", [])
                user.setdefault("notes", [])
                user.setdefault("folders", [])
                user.setdefault("exam_folders", [])
                user.setdefault("exam_folder_analyses", {})
                user.setdefault("exam_documents", {})
                user.setdefault("documents", {})
                user.setdefault("sessions", [])
            return migrated

        legacy_tags = loaded.get("tags", [])
        legacy_notes = loaded.get("notes", [])
        if legacy_tags or legacy_notes:
            user = self._get_or_create_user_unlocked("legacy")
            user["tags"] = [tag for tag in legacy_tags if isinstance(tag, str)]
            user["notes"] = [note for note in legacy_notes if isinstance(note, dict)]

        return migrated

    def load(self) -> None:
        with self._lock:
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as file:
                        self.data = self._migrate(json.load(file))
                except json.JSONDecodeError:
                    self.data = self._default_data()
                    self.save()
            else:
                self.save()

    def save(self) -> None:
        with self._lock:
            with open(self.db_path, "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=2)

    def create_user(self, username: str, password_hash: str, password_salt: str) -> Dict[str, Any]:
        with self._lock:
            if username in self.data["users"]:
                raise ValueError("Username already exists")
            user = self._get_or_create_user_unlocked(username)
            user["password_hash"] = password_hash
            user["password_salt"] = password_salt
            self.save()
            return self._public_user(user)

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
            "updated_at": analysis.get("updated_at"),
            "completed_at": analysis.get("completed_at"),
            "error": analysis.get("error"),
            "stale": bool(analysis.get("stale")),
            "job_id": analysis.get("job_id"),
            "model": analysis.get("model"),
            "pipeline_version": analysis.get("pipeline_version"),
            "summary": summary,
        }

    def _mark_exam_folder_analysis_stale_unlocked(self, user: Dict[str, Any], folder_ids: List[Optional[str]]) -> bool:
        analyses = user.setdefault("exam_folder_analyses", {})
        changed = False
        for folder_id in folder_ids:
            if not folder_id:
                continue
            analysis = analyses.get(folder_id)
            if not isinstance(analysis, dict):
                continue
            analysis["stale"] = True
            analysis["updated_at"] = self._now_iso()
            changed = True
        return changed

    def get_user_credentials(self, username: str) -> Optional[Dict[str, str]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            return {
                "password_hash": user.get("password_hash", ""),
                "password_salt": user.get("password_salt", ""),
            }

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            return self._public_user(user)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.get_user(username)

    @staticmethod
    def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "created_at": user.get("created_at"),
        }

    def create_session(self, username: str, session_id: str, session_hash: str, expires_at: str) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")
            session = {
                "id": session_id,
                "hash": session_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at,
            }
            user.setdefault("sessions", []).append(session)
            self.save()
            return dict(session)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for username, user in self.data["users"].items():
                for session in user.get("sessions", []):
                    if session.get("id") == session_id:
                        return {"username": username, **session}
            return None

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            for user in self.data["users"].values():
                sessions = user.get("sessions", [])
                next_sessions = [session for session in sessions if session.get("id") != session_id]
                if len(next_sessions) != len(sessions):
                    user["sessions"] = next_sessions
                    self.save()
                    return True
            return False

    def get_tags(self, username: str) -> List[str]:
        with self._lock:
            user = self.data["users"].get(username)
            return list(user.get("tags", [])) if user else []

    def add_tag(self, username: str, tag: str) -> bool:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return False
            tags = user.setdefault("tags", [])
            if tag not in tags:
                tags.append(tag)
                self.save()
                return True
            return False

    def delete_tag(self, username: str, tag: str) -> bool:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return False
            tags = user.setdefault("tags", [])
            if tag in tags:
                tags.remove(tag)
                self.save()
                return True
            return False

    def get_notes(self, username: str) -> List[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            return list(user.get("notes", [])) if user else []

    def list_folders(self, username: str) -> List[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return []
            folders = user.setdefault("folders", [])
            return sorted(
                [dict(folder) for folder in folders if isinstance(folder, dict)],
                key=lambda folder: (folder.get("name") or "").lower(),
            )

    def get_folder(self, username: str, folder_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            for folder in user.setdefault("folders", []):
                if folder.get("id") == folder_id:
                    return dict(folder)
            return None

    def create_folder(self, username: str, name: str) -> Dict[str, Any]:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Folder name is required")

        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")

            folders = user.setdefault("folders", [])
            if any(
                isinstance(folder, dict)
                and (folder.get("name") or "").strip().lower() == normalized_name.lower()
                for folder in folders
            ):
                raise ValueError("Folder already exists")

            folder = {
                "id": uuid.uuid4().hex,
                "name": normalized_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            folders.append(folder)
            self.save()
            return dict(folder)

    def list_exam_folders(self, username: str) -> List[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return []
            folders = user.setdefault("exam_folders", [])
            analyses = user.setdefault("exam_folder_analyses", {})
            return sorted(
                [
                    {
                        **dict(folder),
                        "analysis": self._analysis_summary(analyses.get(folder.get("id"))),
                    }
                    for folder in folders
                    if isinstance(folder, dict)
                ],
                key=lambda folder: (folder.get("name") or "").lower(),
            )

    def get_exam_folder(self, username: str, folder_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            for folder in user.setdefault("exam_folders", []):
                if folder.get("id") == folder_id:
                    return dict(folder)
            return None

    def create_exam_folder(self, username: str, name: str) -> Dict[str, Any]:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Folder name is required")

        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")

            folders = user.setdefault("exam_folders", [])
            if any(
                isinstance(folder, dict)
                and (folder.get("name") or "").strip().lower() == normalized_name.lower()
                for folder in folders
            ):
                raise ValueError("Folder already exists")

            folder = {
                "id": uuid.uuid4().hex,
                "name": normalized_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            folders.append(folder)
            self.save()
            return dict(folder)

    def get_exam_folder_analysis(self, username: str, folder_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            analysis = user.setdefault("exam_folder_analyses", {}).get(folder_id)
            return dict(analysis) if isinstance(analysis, dict) else None

    def save_exam_folder_analysis(self, username: str, folder_id: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")
            analyses = user.setdefault("exam_folder_analyses", {})
            analyses[folder_id] = dict(analysis)
            self.save()
            return dict(analyses[folder_id])

    def update_exam_folder_analysis(
        self,
        username: str,
        folder_id: str,
        **updates: Any,
    ) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")
            analyses = user.setdefault("exam_folder_analyses", {})
            current = analyses.get(folder_id)
            if not isinstance(current, dict):
                current = {
                    "folder_id": folder_id,
                    "status": "idle",
                    "stage": "",
                    "progress": 0,
                    "summary": {},
                    "result": None,
                    "error": None,
                    "stale": False,
                    "created_at": self._now_iso(),
                }
            next_analysis = dict(current)
            next_analysis.update(updates)
            next_analysis["updated_at"] = self._now_iso()
            analyses[folder_id] = next_analysis
            self.save()
            return dict(next_analysis)

    def add_note(self, username: str, content: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            note = {
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            user.setdefault("notes", []).append(note)
            self.save()
            return note

    def delete_note(self, username: str, note_id: str) -> bool:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return False
            notes = user.setdefault("notes", [])
            next_notes = [note for note in notes if note.get("id") != note_id]
            if len(next_notes) != len(notes):
                user["notes"] = next_notes
                self.save()
                return True
            return False

    def set_document_metadata(self, username: str, filename: str, metadata: Dict[str, Any]) -> None:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return
            documents = user.setdefault("documents", {})
            existing = documents.get(filename, {})
            next_metadata = dict(existing) if isinstance(existing, dict) else {}
            next_metadata.update(metadata)
            documents[filename] = next_metadata
            self.save()

    def get_document_metadata(self, username: str, filename: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            documents = user.setdefault("documents", {})
            metadata = documents.get(filename)
            return dict(metadata) if isinstance(metadata, dict) else None

    def set_document_folder(self, username: str, filename: str, folder_id: Optional[str]) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")

            documents = user.setdefault("documents", {})
            if filename not in documents:
                documents[filename] = {}

            folder_name = None
            normalized_folder_id = folder_id or None
            if normalized_folder_id:
                folder = None
                for item in user.setdefault("folders", []):
                    if item.get("id") == normalized_folder_id:
                        folder = item
                        break
                if not folder:
                    raise ValueError("Folder not found")
                folder_name = folder.get("name")

            next_metadata = dict(documents.get(filename, {}))
            next_metadata["folder_id"] = normalized_folder_id
            next_metadata["folder_name"] = folder_name
            documents[filename] = next_metadata
            self.save()
            return dict(next_metadata)

    def list_exam_documents(self, username: str) -> List[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return []
            documents = user.setdefault("exam_documents", {})
            return sorted(
                [dict(item) for item in documents.values() if isinstance(item, dict)],
                key=lambda item: ((item.get("folder_name") or "").lower(), (item.get("filename") or "").lower()),
            )

    def add_exam_document(self, username: str, document: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")
            doc_id = document.get("id") or uuid.uuid4().hex
            next_document = dict(document)
            next_document["id"] = doc_id
            user.setdefault("exam_documents", {})[doc_id] = next_document
            self._mark_exam_folder_analysis_stale_unlocked(user, [next_document.get("folder_id")])
            self.save()
            return dict(next_document)

    def get_exam_document(self, username: str, document_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return None
            document = user.setdefault("exam_documents", {}).get(document_id)
            return dict(document) if isinstance(document, dict) else None

    def update_exam_document_folder(self, username: str, document_id: str, folder_id: str) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                raise ValueError("User not found")

            document = user.setdefault("exam_documents", {}).get(document_id)
            if not isinstance(document, dict):
                raise ValueError("Exam document not found")

            folder = None
            for item in user.setdefault("exam_folders", []):
                if item.get("id") == folder_id:
                    folder = item
                    break
            if not folder:
                raise ValueError("Folder not found")

            previous_folder_id = document.get("folder_id")
            document["folder_id"] = folder["id"]
            document["folder_name"] = folder["name"]
            self._mark_exam_folder_analysis_stale_unlocked(user, [previous_folder_id, folder["id"]])
            self.save()
            return dict(document)

    def delete_document_metadata(self, username: str, filename: str) -> bool:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return False
            documents = user.setdefault("documents", {})
            if filename in documents:
                del documents[filename]
                self.save()
                return True
            return False

    def get_all_metadata(self, username: str) -> Dict[str, Any]:
        with self._lock:
            user = self.data["users"].get(username)
            if not user:
                return {}
            return user.get("documents", {})
