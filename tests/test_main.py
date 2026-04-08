from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock


def test_get_frontend_asset_version_uses_existing_files(main_module, tmp_path, monkeypatch):
    js_path = tmp_path / "index.js"
    css_path = tmp_path / "index.css"
    js_path.write_text("console.log('hi');", encoding="utf-8")
    css_path.write_text("body {}", encoding="utf-8")

    monkeypatch.setattr(main_module, "FRONTEND_ENTRY_JS", js_path)
    monkeypatch.setattr(main_module, "FRONTEND_ENTRY_CSS", css_path)

    version = main_module.get_frontend_asset_version()

    assert version
    assert "-" in version


def test_save_upload_file_copies_binary_content(main_module, tmp_path):
    destination = tmp_path / "copy.bin"

    main_module._save_upload_file(BytesIO(b"study-space"), destination)

    assert destination.read_bytes() == b"study-space"


def test_ensure_selected_files_owned_returns_owned_files(main_module):
    main_module.vector_store.get_document_metadata.side_effect = [
        {"filename": "one.pdf"},
        {"filename": "two.pdf"},
    ]

    selected = main_module._ensure_selected_files_owned("alice", ["one.pdf", "two.pdf"])

    assert selected == ["one.pdf", "two.pdf"]


def test_upload_job_manager_processes_document_successfully(main_module, tmp_path, monkeypatch):
    processor = MagicMock()
    processor.process_document.return_value = "# Notes"
    processor.classify_content_full.return_value = {
        "labels": ["Security", "Forensics"],
        "scores": [0.9, 0.1],
    }
    database = MagicMock()
    database.get_user.return_value = {"username": "alice"}
    database.get_tags.return_value = ["Security"]
    extractor = MagicMock()
    extractor.extract_metadata.return_value = {"assessments": [], "deadlines": [], "contacts": []}
    store = MagicMock()

    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    monkeypatch.setattr(main_module, "_user_processed_dir", lambda username: processed_dir)

    upload_path = tmp_path / "upload.pdf"
    upload_path.write_text("binary placeholder", encoding="utf-8")

    manager = main_module.UploadJobManager(processor, database, store, extractor)
    job = manager.enqueue("alice", "upload.pdf", upload_path)

    manager._process_job(job["job_id"])
    completed_job = manager.get_job("alice", job["job_id"])

    assert completed_job["status"] == main_module.UploadJobStatus.COMPLETED.value
    assert completed_job["predicted_tag"] == "Security"
    assert completed_job["doc_id"].startswith("upload.pdf_")
    database.add_tag.assert_called_once_with("alice", "Security")
    from unittest.mock import ANY
    database.set_document_metadata.assert_called_once_with(
        "alice",
        "upload.pdf",
        {
            "assessments": [],
            "deadlines": [],
            "contacts": [],
            "filename": "upload.pdf",
            "path": ANY,
            "processed_path": ANY,
            "folder_id": None,
            "folder_name": None,
            "tag": "Security",
        },
    )
    store.add_document.assert_called_once()
    assert list(processed_dir.glob("*.md"))


def test_upload_job_manager_marks_failed_jobs_and_cleans_up_file(main_module, tmp_path):
    processor = MagicMock()
    database = MagicMock()
    database.get_user.return_value = None
    extractor = MagicMock()
    store = MagicMock()

    upload_path = tmp_path / "broken.pdf"
    upload_path.write_text("temporary file", encoding="utf-8")

    manager = main_module.UploadJobManager(processor, database, store, extractor)
    job = manager.enqueue("alice", "broken.pdf", upload_path)

    manager._process_job(job["job_id"])
    failed_job = manager.get_job("alice", job["job_id"])

    assert failed_job["status"] == main_module.UploadJobStatus.FAILED.value
    assert "Owner not found" in failed_job["error"]
    assert not upload_path.exists()


def test_trim_history_keeps_active_jobs_and_latest_finished(main_module, tmp_path):
    manager = main_module.UploadJobManager(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        max_history=2,
    )

    old_finished = main_module.UploadJob(
        job_id="old",
        owner_username="alice",
        filename="old.pdf",
        file_path=str(tmp_path / "old.pdf"),
        status=main_module.UploadJobStatus.COMPLETED.value,
        stage="Completed",
        progress=100,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        created_ts=1.0,
        updated_ts=1.0,
    )
    recent_finished = main_module.UploadJob(
        job_id="recent",
        owner_username="alice",
        filename="recent.pdf",
        file_path=str(tmp_path / "recent.pdf"),
        status=main_module.UploadJobStatus.COMPLETED.value,
        stage="Completed",
        progress=100,
        created_at="2026-01-02T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        created_ts=2.0,
        updated_ts=2.0,
    )
    active = main_module.UploadJob(
        job_id="active",
        owner_username="alice",
        filename="active.pdf",
        file_path=str(tmp_path / "active.pdf"),
        status=main_module.UploadJobStatus.QUEUED.value,
        stage="Queued",
        progress=0,
        created_at="2026-01-03T00:00:00+00:00",
        updated_at="2026-01-03T00:00:00+00:00",
        created_ts=3.0,
        updated_ts=3.0,
    )

    manager._jobs = {"old": old_finished, "recent": recent_finished, "active": active}
    manager._trim_history_unlocked()

    assert set(manager._jobs) == {"recent", "active"}
