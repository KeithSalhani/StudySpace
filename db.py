import json
import os
from typing import List, Dict, Any
from datetime import datetime
import uuid
import threading

class JSONDatabase:
    def __init__(self, db_path: str = "db.json"):
        self._lock = threading.RLock()
        self.db_path = db_path
        self.data = {
            "tags": [],
            "notes": []
        }
        self.load()

    def load(self):
        with self._lock:
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, 'r') as f:
                        self.data = json.load(f)
                except json.JSONDecodeError:
                    # If file is corrupted or empty, start fresh
                    self.save()
            else:
                self.save()

    def save(self):
        with self._lock:
            with open(self.db_path, 'w') as f:
                json.dump(self.data, f, indent=2)

    # Tag Operations
    def get_tags(self) -> List[str]:
        with self._lock:
            return list(self.data.get("tags", []))

    def add_tag(self, tag: str) -> bool:
        with self._lock:
            if tag not in self.data["tags"]:
                self.data["tags"].append(tag)
                self.save()
                return True
            return False

    def delete_tag(self, tag: str) -> bool:
        with self._lock:
            if tag in self.data["tags"]:
                self.data["tags"].remove(tag)
                self.save()
                return True
            return False

    # Note Operations
    def get_notes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.data.get("notes", []))

    def add_note(self, content: str) -> Dict[str, Any]:
        with self._lock:
            note = {
                "id": str(uuid.uuid4()),
                "content": content,
                "created_at": datetime.now().isoformat()
            }
            self.data["notes"].append(note)
            self.save()
            return note

    def delete_note(self, note_id: str) -> bool:
        with self._lock:
            original_length = len(self.data["notes"])
            self.data["notes"] = [n for n in self.data["notes"] if n["id"] != note_id]
            if len(self.data["notes"]) < original_length:
                self.save()
                return True
            return False
