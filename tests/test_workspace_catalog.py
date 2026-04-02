from types import SimpleNamespace

from app.core.workspace_catalog import build_workspace_catalog, build_workspace_catalog_snapshot
from app.db.metadata import JSONDatabase


def test_build_workspace_catalog_returns_compact_tag_map(tmp_path):
    db = JSONDatabase(str(tmp_path / "catalog.json"))
    db.create_user("alice", "hash", "salt")

    vector_store = SimpleNamespace(
        list_documents=lambda username: [
            {"filename": "lecture1.pdf", "tag": "Security"},
            {"filename": "notes.pdf", "tag": "Artificial Intelligence"},
            {"filename": "exam-2024.pdf", "tag": "Exam Papers"},
        ]
        if username == "alice"
        else [
            {"filename": "bob-only.pdf", "tag": "Security"},
        ]
    )

    catalog = build_workspace_catalog("alice", db, vector_store)

    assert catalog == {
        "tags": {
            "Artificial Intelligence": ["notes.pdf"],
            "Exam Papers": ["exam-2024.pdf"],
            "Security": ["lecture1.pdf"],
        }
    }


def test_build_workspace_catalog_snapshot_deduplicates_and_keeps_untagged_files():
    catalog = build_workspace_catalog_snapshot(
        searchable_documents=[
            {"filename": "week1.pdf", "tag": "Security"},
            {"filename": "week1.pdf", "tag": "Security"},
            {"filename": "week2.pdf", "tag": "Uncategorized"},
            {"filename": "week3.pdf", "tag": None},
            {"filename": "week4.pdf", "tag": "Exam Papers"},
        ]
    )

    assert catalog == {
        "tags": {
            "Exam Papers": ["week4.pdf"],
            "Security": ["week1.pdf"],
        },
        "untagged_files": ["week2.pdf", "week3.pdf"],
    }


def test_build_workspace_catalog_only_requests_the_current_users_documents(tmp_path):
    db = JSONDatabase(str(tmp_path / "catalog.json"))
    db.create_user("alice", "hash", "salt")
    db.create_user("bob", "hash", "salt")

    calls = []

    def list_documents(username):
        calls.append(username)
        if username == "alice":
            return [{"filename": "alice.pdf", "tag": "Security"}]
        return [{"filename": "bob.pdf", "tag": "Security"}]

    vector_store = SimpleNamespace(list_documents=list_documents)

    catalog = build_workspace_catalog("alice", db, vector_store)

    assert calls == ["alice"]
    assert catalog == {"tags": {"Security": ["alice.pdf"]}}
