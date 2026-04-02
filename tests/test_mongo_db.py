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
