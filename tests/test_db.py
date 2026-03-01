import pytest
import json
import os
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
    
    with open(db_file) as f:
        data = json.load(f)
        assert data == {"tags": [], "notes": []}

def test_add_tag(db):
    assert db.add_tag("New Tag") is True
    assert "New Tag" in db.get_tags()
    
    # Duplicate
    assert db.add_tag("New Tag") is False

def test_delete_tag(db):
    db.add_tag("Tag 1")
    assert db.delete_tag("Tag 1") is True
    assert "Tag 1" not in db.get_tags()
    
    # Non-existent
    assert db.delete_tag("Tag 1") is False

def test_add_note(db):
    note = db.add_note("My note content")
    assert note["content"] == "My note content"
    assert "id" in note
    assert "created_at" in note
    
    notes = db.get_notes()
    assert len(notes) == 1
    assert notes[0] == note

def test_delete_note(db):
    note = db.add_note("To delete")
    assert db.delete_note(note["id"]) is True
    assert len(db.get_notes()) == 0
    
    # Non-existent
    assert db.delete_note("fake-id") is False

