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
