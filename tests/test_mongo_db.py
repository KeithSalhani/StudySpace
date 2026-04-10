import os
import uuid

import pytest
MongoClient = pytest.importorskip("pymongo").MongoClient

from app.db.mongo import MongoDatabase


pytestmark = pytest.mark.skipif(
    not os.getenv("MONGODB_TEST_URI"),
    reason="MONGODB_TEST_URI is required for Mongo integration tests",
)


@pytest.fixture
def mongo_db():
    client = MongoClient(os.environ["MONGODB_TEST_URI"])
    db_name = f"studyspace_test_{uuid.uuid4().hex}"
    database = MongoDatabase(client, db_name)
    database.ensure_indexes()
    try:
        yield database
    finally:
        client.drop_database(db_name)
        client.close()


def test_create_user_and_session_roundtrip(mongo_db):
    user = mongo_db.create_user("alice", "hash", "salt")
    mongo_db.create_session("alice", "session-1", "session-hash", "2099-01-01T00:00:00+00:00")

    session = mongo_db.get_session("session-1")

    assert user["username"] == "alice"
    assert session["username"] == "alice"
    assert session["hash"] == "session-hash"


def test_folder_and_document_metadata_roundtrip(mongo_db):
    mongo_db.create_user("alice", "hash", "salt")
    folder = mongo_db.create_folder("alice", "Past Papers")
    mongo_db.set_document_metadata("alice", "exam.pdf", {"assessments": []})

    updated = mongo_db.set_document_folder("alice", "exam.pdf", folder["id"])

    assert updated["folder_id"] == folder["id"]
    assert mongo_db.get_all_metadata("alice")["exam.pdf"]["folder_name"] == "Past Papers"


def test_exam_folder_analysis_becomes_stale_when_document_moves(mongo_db):
    mongo_db.create_user("alice", "hash", "salt")
    security = mongo_db.create_exam_folder("alice", "Security")
    networks = mongo_db.create_exam_folder("alice", "Networks")
    mongo_db.update_exam_folder_analysis(
        "alice",
        security["id"],
        folder_name=security["name"],
        status="completed",
        stage="Topic mining complete",
        progress=100,
        model="gemini-test",
        pipeline_version="topic-miner-v1",
        summary={"paper_count": 1},
        result={"themes": []},
        error=None,
        stale=False,
    )
    mongo_db.update_exam_folder_analysis(
        "alice",
        networks["id"],
        folder_name=networks["name"],
        status="completed",
        stage="Topic mining complete",
        progress=100,
        model="gemini-test",
        pipeline_version="topic-miner-v1",
        summary={"paper_count": 1},
        result={"themes": []},
        error=None,
        stale=False,
    )

    mongo_db.add_exam_document(
        "alice",
        {
            "id": "paper-1",
            "filename": "security.pdf",
            "folder_id": security["id"],
            "folder_name": security["name"],
            "path": "/tmp/security.pdf",
            "created_at": "2026-03-25T18:00:00+00:00",
            "content_type": "application/pdf",
        },
    )
    moved = mongo_db.update_exam_document_folder("alice", "paper-1", networks["id"])

    assert moved["folder_id"] == networks["id"]
    assert mongo_db.get_exam_folder_analysis("alice", security["id"])["stale"] is True
    assert mongo_db.get_exam_folder_analysis("alice", networks["id"])["stale"] is True


def test_get_raw_user_aggregates_all_owned_data(mongo_db):
    mongo_db.create_user("alice", "hash", "salt")
    mongo_db.create_session("alice", "session-1", "session-hash", "2099-01-01T00:00:00+00:00")
    mongo_db.add_tag("alice", "AI")
    note = mongo_db.add_note("alice", "Revise lecture 4")
    study_folder = mongo_db.create_folder("alice", "Past Papers")
    exam_folder = mongo_db.create_exam_folder("alice", "Security")
    mongo_db.set_document_metadata("alice", "exam.pdf", {"tag": "AI", "folder_id": study_folder["id"]})
    mongo_db.update_exam_folder_analysis(
        "alice",
        exam_folder["id"],
        folder_name=exam_folder["name"],
        status="completed",
        stage="Topic mining complete",
        progress=100,
        model="gemini-test",
        pipeline_version="topic-miner-v1",
        summary={"paper_count": 1},
        result={"themes": ["Auth"]},
        error=None,
        stale=False,
    )
    mongo_db.add_exam_document(
        "alice",
        {
            "id": "paper-1",
            "filename": "security.pdf",
            "folder_id": exam_folder["id"],
            "folder_name": exam_folder["name"],
            "path": "/tmp/security.pdf",
            "created_at": "2026-03-25T18:00:00+00:00",
            "content_type": "application/pdf",
        },
    )

    raw_user = mongo_db.get_raw_user("alice")

    assert raw_user is not None
    assert raw_user["username"] == "alice"
    assert raw_user["password_hash"] == "hash"
    assert raw_user["tags"] == ["AI"]
    assert raw_user["notes"][0]["id"] == note["id"]
    assert raw_user["folders"][0]["name"] == "Past Papers"
    assert raw_user["exam_folders"][0]["name"] == "Security"
    assert raw_user["documents"]["exam.pdf"]["tag"] == "AI"
    assert raw_user["exam_folder_analyses"][exam_folder["id"]]["status"] == "completed"
    assert raw_user["exam_documents"]["paper-1"]["filename"] == "security.pdf"
    assert raw_user["sessions"][0]["id"] == "session-1"
    assert raw_user["sessions"][0]["hash"] == "session-hash"


def test_delete_user_removes_user_and_owned_records(mongo_db):
    mongo_db.create_user("alice", "hash", "salt")
    mongo_db.create_session("alice", "session-1", "session-hash", "2099-01-01T00:00:00+00:00")
    mongo_db.add_tag("alice", "AI")
    mongo_db.add_note("alice", "Revise lecture 4")
    study_folder = mongo_db.create_folder("alice", "Past Papers")
    exam_folder = mongo_db.create_exam_folder("alice", "Security")
    mongo_db.set_document_metadata("alice", "exam.pdf", {"tag": "AI", "folder_id": study_folder["id"]})
    mongo_db.update_exam_folder_analysis(
        "alice",
        exam_folder["id"],
        folder_name=exam_folder["name"],
        status="completed",
        stage="Topic mining complete",
        progress=100,
        model="gemini-test",
        pipeline_version="topic-miner-v1",
        summary={"paper_count": 1},
        result={"themes": ["Auth"]},
        error=None,
        stale=False,
    )
    mongo_db.add_exam_document(
        "alice",
        {
            "id": "paper-1",
            "filename": "security.pdf",
            "folder_id": exam_folder["id"],
            "folder_name": exam_folder["name"],
            "path": "/tmp/security.pdf",
            "created_at": "2026-03-25T18:00:00+00:00",
            "content_type": "application/pdf",
        },
    )

    deleted = mongo_db.delete_user("alice")

    assert deleted is True
    assert mongo_db.get_user("alice") is None
    assert mongo_db.get_raw_user("alice") is None
    assert mongo_db.get_session("session-1") is None
    assert mongo_db.get_tags("alice") == []
    assert mongo_db.get_notes("alice") == []
    assert mongo_db.list_folders("alice") == []
    assert mongo_db.list_exam_folders("alice") == []
    assert mongo_db.get_all_metadata("alice") == {}
    assert mongo_db.list_exam_documents("alice") == []


def test_delete_user_returns_false_when_missing(mongo_db):
    assert mongo_db.delete_user("missing") is False
