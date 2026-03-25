import json

import pytest

from app.db.metadata import JSONDatabase


@pytest.fixture
def db_file(tmp_path):
    return tmp_path / "test_db.json"


@pytest.fixture
def db(db_file):
    return JSONDatabase(str(db_file))


def test_init_creates_file(db_file):
    assert not db_file.exists()
    JSONDatabase(str(db_file))
    assert db_file.exists()

    with open(db_file, encoding="utf-8") as file:
        data = json.load(file)
        assert data == {"users": {}}


def test_create_user_and_credentials(db):
    user = db.create_user("alice", "hash", "salt")

    assert user["username"] == "alice"
    assert db.get_user_credentials("alice") == {
        "password_hash": "hash",
        "password_salt": "salt",
    }


def test_tags_are_scoped_per_user(db):
    db.create_user("alice", "hash-a", "salt-a")
    db.create_user("bob", "hash-b", "salt-b")

    assert db.add_tag("alice", "Security") is True
    assert db.add_tag("alice", "Security") is False
    assert db.get_tags("alice") == ["Security"]
    assert db.get_tags("bob") == []


def test_notes_are_scoped_per_user(db):
    db.create_user("alice", "hash-a", "salt-a")
    db.create_user("bob", "hash-b", "salt-b")

    note = db.add_note("alice", "My private note")

    assert note["content"] == "My private note"
    assert len(db.get_notes("alice")) == 1
    assert db.get_notes("bob") == []
    assert db.delete_note("alice", note["id"]) is True
    assert db.delete_note("bob", note["id"]) is False


def test_folders_are_scoped_per_user(db):
    db.create_user("alice", "hash-a", "salt-a")
    db.create_user("bob", "hash-b", "salt-b")

    folder = db.create_folder("alice", "Networks")

    assert folder["name"] == "Networks"
    assert len(db.list_folders("alice")) == 1
    assert db.list_folders("bob") == []
    assert db.get_folder("alice", folder["id"])["name"] == "Networks"


def test_document_folder_assignment_is_persisted(db):
    db.create_user("alice", "hash", "salt")
    folder = db.create_folder("alice", "Past Papers")

    db.set_document_metadata("alice", "exam.pdf", {"assessments": []})
    updated = db.set_document_folder("alice", "exam.pdf", folder["id"])

    assert updated["folder_id"] == folder["id"]
    assert updated["folder_name"] == "Past Papers"
    assert db.get_all_metadata("alice")["exam.pdf"]["folder_name"] == "Past Papers"


def test_sessions_are_scoped_to_user(db):
    db.create_user("alice", "hash-a", "salt-a")

    db.create_session("alice", "session-1", "session-hash", "2099-01-01T00:00:00+00:00")
    session = db.get_session("session-1")

    assert session["username"] == "alice"
    assert session["hash"] == "session-hash"
    assert db.delete_session("session-1") is True
    assert db.get_session("session-1") is None


def test_document_metadata_is_scoped_per_user(db):
    db.create_user("alice", "hash-a", "salt-a")
    db.create_user("bob", "hash-b", "salt-b")

    alice_meta = {"assessments": [{"item": "Exam", "weight": "100%"}]}
    bob_meta = {"assessments": [{"item": "Project", "weight": "50%"}]}

    db.set_document_metadata("alice", "doc1.pdf", alice_meta)
    db.set_document_metadata("bob", "doc2.pdf", bob_meta)

    assert db.get_all_metadata("alice") == {"doc1.pdf": alice_meta}
    assert db.get_all_metadata("bob") == {"doc2.pdf": bob_meta}


def test_delete_document_metadata(db):
    db.create_user("alice", "hash", "salt")
    meta = {"assessments": []}
    
    db.set_document_metadata("alice", "doc1.pdf", meta)
    assert "doc1.pdf" in db.get_all_metadata("alice")
    
    assert db.delete_document_metadata("alice", "doc1.pdf") is True
    assert "doc1.pdf" not in db.get_all_metadata("alice")
    assert db.delete_document_metadata("alice", "nonexistent.pdf") is False


def test_migrate_initializes_documents_field(db_file):
    # Create a legacy DB without the "documents" field
    legacy_data = {
        "users": {
            "alice": {
                "id": "1",
                "username": "alice",
                "password_hash": "h",
                "password_salt": "s",
                "created_at": "2025-01-01T00:00:00Z",
                "tags": ["Tag1"],
                "notes": [{"id": "n1", "content": "note1"}],
                "sessions": []
            }
        }
    }
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)

    # Load DB and check if "documents" was added
    db = JSONDatabase(str(db_file))
    user = db.data["users"]["alice"]
    assert "documents" in user
    assert user["documents"] == {}
    assert user["tags"] == ["Tag1"]
    assert user["notes"][0]["content"] == "note1"
