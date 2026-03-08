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


def test_sessions_are_scoped_to_user(db):
    db.create_user("alice", "hash-a", "salt-a")

    db.create_session("alice", "session-1", "session-hash", "2099-01-01T00:00:00+00:00")
    session = db.get_session("session-1")

    assert session["username"] == "alice"
    assert session["hash"] == "session-hash"
    assert db.delete_session("session-1") is True
    assert db.get_session("session-1") is None
