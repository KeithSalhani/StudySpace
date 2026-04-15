"""
RAG Chat Application for Student Study Hub
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional
from zipfile import ZIP_DEFLATED, ZipFile

import asyncio
import json
import logging
import os
import shutil
import threading
import time
import uuid

from pymongo import MongoClient
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.auth import (
    AuthenticatedUser,
    SESSION_COOKIE_NAME,
    create_password_record,
    create_session_for_user,
    get_current_user,
    validate_password,
    validate_username,
    verify_password,
)
from app.config import (
    GEMINI_API_KEY,
    MONGODB_APP_NAME,
    MONGODB_DB_NAME,
    MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    MONGODB_URI,
    PROCESSED_DIR,
    SESSION_COOKIE_SECURE,
    STATIC_DIR,
    TEMPLATES_DIR,
    UPLOAD_DIR,
    USERS_DIR,
)
from app.core.ingestion import DocumentProcessor
from app.db.vector_store import VectorStore
from app.core.rag import RAGChat
from app.core.quiz_generator import QuizGenerator
from app.core.flashcard_generator import FlashcardGenerator
from app.core.study_set_generator import ALLOWED_STUDY_SET_TYPES, StudySetGenerator
from app.core.metadata_extractor import MetadataExtractor
from app.core.topic_miner import TopicMiner
from app.db.mongo import MongoDatabase
from app.db.repository import DatabaseRepository

logger = logging.getLogger(__name__)

# Check for API key
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable must be set. Please check config.py")
FRONTEND_DIST_DIR = STATIC_DIR / "dist"
FRONTEND_ENTRY_JS = FRONTEND_DIST_DIR / "assets" / "index.js"
FRONTEND_ENTRY_CSS = FRONTEND_DIST_DIR / "assets" / "index.css"

# Initialize components
doc_processor = DocumentProcessor()
vector_store = VectorStore()
rag_chat = RAGChat(vector_store, GEMINI_API_KEY)
quiz_generator = QuizGenerator(PROCESSED_DIR, GEMINI_API_KEY)
flashcard_generator = FlashcardGenerator(PROCESSED_DIR, GEMINI_API_KEY)
study_set_generator = StudySetGenerator(PROCESSED_DIR, GEMINI_API_KEY)
metadata_extractor = MetadataExtractor(GEMINI_API_KEY)
topic_miner = TopicMiner(doc_processor, GEMINI_API_KEY)
db: Optional[DatabaseRepository] = None
mongo_client: Optional[MongoClient] = None


def _user_root(username: str) -> Path:
    path = USERS_DIR / username
    path.mkdir(parents=True, exist_ok=True)
    return path


def _user_upload_dir(username: str) -> Path:
    path = _user_root(username) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _user_processed_dir(username: str) -> Path:
    path = _user_root(username) / "processed"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _user_exam_papers_dir(username: str) -> Path:
    path = _user_root(username) / "exam_papers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
        expires=int(expires_at.timestamp()),
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def _database() -> DatabaseRepository:
    if db is None:
        raise RuntimeError("Database is not initialized")
    return db


def get_frontend_asset_version() -> str:
    timestamps = []
    for path in (FRONTEND_ENTRY_JS, FRONTEND_ENTRY_CSS):
        if path.exists():
            timestamps.append(str(int(path.stat().st_mtime)))
    return "-".join(timestamps) if timestamps else "dev"


class UploadJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UploadJob:
    job_id: str
    owner_username: str
    filename: str
    file_path: str
    status: str
    stage: str
    progress: int
    created_at: str
    updated_at: str
    created_ts: float
    updated_ts: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    doc_id: Optional[str] = None
    predicted_tag: Optional[str] = None
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None


@dataclass
class TopicMiningJob:
    job_id: str
    owner_username: str
    folder_id: str
    folder_name: str
    status: str
    stage: str
    progress: int
    created_at: str
    updated_at: str
    created_ts: float
    updated_ts: float
    total_documents: int
    model: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class UploadJobManager:
    def __init__(
        self,
        processor: DocumentProcessor,
        database: Optional[DatabaseRepository],
        store: VectorStore,
        extractor: MetadataExtractor,
        max_history: int = 100,
    ):
        self.processor = processor
        self.database = database
        self.store = store
        self.extractor = extractor
        self.max_history = max_history

        self._jobs: Dict[str, UploadJob] = {}
        self._pending_order: List[str] = []
        self._queue: Queue[Optional[str]] = Queue()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None

    def start(self) -> None:
        with self._lock:
            if self._worker and self._worker.is_alive():
                return
            self._stop_event.clear()
            self._worker = threading.Thread(target=self._worker_loop, name="upload-worker", daemon=True)
            self._worker.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        self._queue.put(None)
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=timeout)

    def enqueue(
        self,
        owner_username: str,
        filename: str,
        file_path: Path,
        folder_id: Optional[str] = None,
        folder_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        now, now_ts = self._now()
        job = UploadJob(
            job_id=uuid.uuid4().hex,
            owner_username=owner_username,
            filename=filename,
            file_path=str(file_path),
            status=UploadJobStatus.QUEUED.value,
            stage="Queued for processing",
            progress=0,
            created_at=now,
            updated_at=now,
            created_ts=now_ts,
            updated_ts=now_ts,
            folder_id=folder_id,
            folder_name=folder_name,
        )

        with self._lock:
            self._jobs[job.job_id] = job
            self._pending_order.append(job.job_id)
            self._trim_history_unlocked()

        self._queue.put(job.job_id)
        return self._to_public(job)

    def list_jobs(self, owner_username: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = [
                job for job in self._jobs.values() if job.owner_username == owner_username
            ]
            jobs = sorted(jobs, key=lambda item: item.created_ts, reverse=True)
            if limit > 0:
                jobs = jobs[:limit]
            return [self._to_public(job) for job in jobs]

    def get_job(self, owner_username: str, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.owner_username != owner_username:
                return None
            return self._to_public(job)

    @staticmethod
    def _now() -> tuple[str, float]:
        dt = datetime.now(timezone.utc)
        return dt.isoformat(), dt.timestamp()

    def _to_public(self, job: UploadJob) -> Dict[str, Any]:
        item = asdict(job)
        item.pop("file_path", None)
        item.pop("created_ts", None)
        item.pop("updated_ts", None)
        item.pop("owner_username", None)
        item["queue_position"] = None

        if item["status"] == UploadJobStatus.QUEUED.value:
            with self._lock:
                if job.job_id in self._pending_order:
                    item["queue_position"] = self._pending_order.index(job.job_id) + 1

        return item

    def _update_job(self, job_id: str, **updates: Any) -> Optional[UploadJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            for key, value in updates.items():
                setattr(job, key, value)

            now, now_ts = self._now()
            job.updated_at = now
            job.updated_ts = now_ts
            return job

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id = self._queue.get(timeout=0.5)
            except Empty:
                continue

            if job_id is None:
                break

            with self._lock:
                if job_id in self._pending_order:
                    self._pending_order.remove(job_id)

            try:
                self._process_job(job_id)
            finally:
                self._queue.task_done()

    def _process_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            owner_username = job.owner_username
            filename = job.filename
            file_path = Path(job.file_path)
            folder_id = job.folder_id
            folder_name = job.folder_name

        started_at, _ = self._now()
        started = time.perf_counter()

        self._update_job(
            job_id,
            status=UploadJobStatus.PROCESSING.value,
            stage="Extracting text",
            progress=15,
            started_at=started_at,
        )

        try:
            if self.database is None:
                raise RuntimeError("Database is not initialized")

            owner = self.database.get_user(owner_username)
            if not owner:
                raise ValueError("Owner not found for upload job")

            content = self.processor.process_document(str(file_path))

            self._update_job(job_id, stage="Saving processed file", progress=35)
            processed_path = _user_processed_dir(owner_username) / f"{uuid.uuid4().hex}_{filename}.md"
            with open(processed_path, "w", encoding="utf-8") as out_file:
                out_file.write(content)

            self._update_job(job_id, stage="Classifying document", progress=55)
            current_tags = self.database.get_tags(owner_username)
            if not current_tags:
                current_tags = ["Forensics", "Machine Learning", "Security", "Study Material"]

            classification_result = self.processor.classify_content_full(content, current_tags)
            predicted_tag = None
            if classification_result:
                predicted_tag = classification_result["labels"][0]
                logger.info("Categorization for %s", filename)
                for label, score in zip(classification_result["labels"], classification_result["scores"]):
                    logger.info("  %s: %.2f%%", label, score * 100)

            if predicted_tag:
                self.database.add_tag(owner_username, predicted_tag)

            self._update_job(job_id, stage="Extracting academic metadata", progress=70)
            extracted_metadata = self.extractor.extract_metadata(content)
            self.database.set_document_metadata(
                owner_username,
                filename,
                {
                    **extracted_metadata,
                    "filename": filename,
                    "path": str(file_path),
                    "processed_path": str(processed_path),
                    "folder_id": folder_id,
                    "folder_name": folder_name,
                    "tag": predicted_tag,
                },
            )

            self._update_job(job_id, stage="Indexing in vector database", progress=85)
            doc_id = f"{filename}_{uuid.uuid4().hex[:8]}"
            metadata = {
                "owner_username": owner_username,
                "filename": filename,
                "path": str(file_path),
                "processed_path": str(processed_path),
                "tag": predicted_tag,
                "folder_id": folder_id,
                "folder_name": folder_name,
            }
            try:
                self.store.add_document(doc_id, content, metadata)
            except Exception:
                self.database.delete_document_metadata(owner_username, filename)
                raise

            elapsed = round(time.perf_counter() - started, 2)
            finished_at, _ = self._now()
            self._update_job(
                job_id,
                status=UploadJobStatus.COMPLETED.value,
                stage="Completed",
                progress=100,
                completed_at=finished_at,
                processing_time_seconds=elapsed,
                predicted_tag=predicted_tag,
                doc_id=doc_id,
            )

        except Exception as exc:
            logger.exception("Upload job failed: %s", job_id)
            finished_at, _ = self._now()
            elapsed = round(time.perf_counter() - started, 2)
            self._update_job(
                job_id,
                status=UploadJobStatus.FAILED.value,
                stage="Failed",
                progress=100,
                completed_at=finished_at,
                processing_time_seconds=elapsed,
                error=str(exc),
            )
            try:
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
            except Exception as cleanup_exc:
                logger.warning(
                    "Failed to remove failed upload file %s: %s",
                    file_path,
                    cleanup_exc,
                )
        finally:
            with self._lock:
                self._trim_history_unlocked()

    def _trim_history_unlocked(self) -> None:
        if len(self._jobs) <= self.max_history:
            return

        active = {
            job_id
            for job_id, job in self._jobs.items()
            if job.status in {UploadJobStatus.QUEUED.value, UploadJobStatus.PROCESSING.value}
        }

        finished = [
            (job_id, job.updated_ts)
            for job_id, job in self._jobs.items()
            if job.status in {UploadJobStatus.COMPLETED.value, UploadJobStatus.FAILED.value}
        ]
        finished.sort(key=lambda item: item[1], reverse=True)

        keep_finished_count = max(0, self.max_history - len(active))
        keep_finished_ids = {job_id for job_id, _ in finished[:keep_finished_count]}
        keep = active.union(keep_finished_ids)

        for job_id in list(self._jobs.keys()):
            if job_id not in keep:
                self._jobs.pop(job_id, None)
                if job_id in self._pending_order:
                    self._pending_order.remove(job_id)


class TopicMiningJobManager:
    def __init__(
        self,
        miner: TopicMiner,
        database: Optional[DatabaseRepository],
        max_history: int = 50,
    ):
        self.miner = miner
        self.database = database
        self.max_history = max_history

        self._jobs: Dict[str, TopicMiningJob] = {}
        self._pending_order: List[str] = []
        self._queue: Queue[Optional[str]] = Queue()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None

    def start(self) -> None:
        with self._lock:
            if self._worker and self._worker.is_alive():
                return
            self._stop_event.clear()
            self._worker = threading.Thread(
                target=self._worker_loop,
                name="topic-miner-worker",
                daemon=True,
            )
            self._worker.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        self._queue.put(None)
        worker = self._worker
        if worker and worker.is_alive():
            worker.join(timeout=timeout)

    def enqueue(
        self,
        owner_username: str,
        folder_id: str,
        folder_name: str,
        total_documents: int,
    ) -> Dict[str, Any]:
        if self.database is None:
            raise RuntimeError("Database is not initialized")

        existing = self.database.get_exam_folder_analysis(owner_username, folder_id)
        if isinstance(existing, dict) and existing.get("status") in {
            UploadJobStatus.QUEUED.value,
            UploadJobStatus.PROCESSING.value,
        }:
            raise ValueError("Topic mining is already running for this folder")

        now, now_ts = self._now()
        job = TopicMiningJob(
            job_id=uuid.uuid4().hex,
            owner_username=owner_username,
            folder_id=folder_id,
            folder_name=folder_name,
            status=UploadJobStatus.QUEUED.value,
            stage="Queued for topic mining",
            progress=0,
            created_at=now,
            updated_at=now,
            created_ts=now_ts,
            updated_ts=now_ts,
            total_documents=total_documents,
            model=self.miner.model_id,
        )

        with self._lock:
            self._jobs[job.job_id] = job
            self._pending_order.append(job.job_id)
            self._trim_history_unlocked()

        self.database.update_exam_folder_analysis(
            owner_username,
            folder_id,
            folder_name=folder_name,
            job_id=job.job_id,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            completed_at=None,
            error=None,
            stale=False,
            model=self.miner.model_id,
            pipeline_version=self.miner.pipeline_version,
            summary={
                "paper_count": total_documents,
                "analyzed_paper_count": 0,
                "theme_count": 0,
                "question_count": 0,
            },
            result=None,
        )
        self._queue.put(job.job_id)
        return self._to_public(job)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id = self._queue.get(timeout=0.5)
            except Empty:
                continue

            if job_id is None:
                if self._stop_event.is_set():
                    break
                continue

            try:
                self._process_job(job_id)
            finally:
                self._queue.task_done()

    def _process_job(self, job_id: str) -> None:
        job = self._update_job(
            job_id,
            status=UploadJobStatus.PROCESSING.value,
            stage="Preparing exam papers",
            progress=5,
        )
        if not job:
            return

        self.database.update_exam_folder_analysis(
            job.owner_username,
            job.folder_id,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            error=None,
        )

        documents = [
            document
            for document in self.database.list_exam_documents(job.owner_username)
            if document.get("folder_id") == job.folder_id
        ]
        if not documents:
            self._fail_job(job_id, "No exam papers found in this folder")
            return

        try:
            result = self.miner.analyze_folder(
                job.folder_name,
                documents,
                progress_callback=lambda stage, progress: self._update_topic_mining_progress(
                    job_id,
                    stage,
                    progress,
                ),
            )
            now, _ = self._now()
            completed_job = self._update_job(
                job_id,
                status=UploadJobStatus.COMPLETED.value,
                stage="Topic mining complete",
                progress=100,
                completed_at=now,
                error=None,
            )
            if not completed_job:
                return

            self.database.update_exam_folder_analysis(
                completed_job.owner_username,
                completed_job.folder_id,
                folder_name=completed_job.folder_name,
                job_id=completed_job.job_id,
                status=completed_job.status,
                stage=completed_job.stage,
                progress=completed_job.progress,
                completed_at=completed_job.completed_at,
                error=None,
                model=result.get("model") or self.miner.model_id,
                pipeline_version=result.get("pipeline_version") or self.miner.pipeline_version,
                summary=result.get("summary") or {},
                result=result,
            )
        except Exception as exc:
            logger.error("Topic mining failed for folder %s: %s", job.folder_name, exc)
            self._fail_job(job_id, str(exc))

    def _update_topic_mining_progress(self, job_id: str, stage: str, progress: int) -> None:
        job = self._update_job(job_id, stage=stage, progress=progress)
        if not job:
            return
        self.database.update_exam_folder_analysis(
            job.owner_username,
            job.folder_id,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            error=None,
        )

    def _fail_job(self, job_id: str, error_message: str) -> None:
        job = self._update_job(
            job_id,
            status=UploadJobStatus.FAILED.value,
            stage="Topic mining failed",
            error=error_message,
        )
        if not job:
            return
        self.database.update_exam_folder_analysis(
            job.owner_username,
            job.folder_id,
            status=job.status,
            stage=job.stage,
            progress=job.progress,
            error=error_message,
            completed_at=None,
        )

    @staticmethod
    def _now() -> tuple[str, float]:
        dt = datetime.now(timezone.utc)
        return dt.isoformat(), dt.timestamp()

    def _update_job(self, job_id: str, **updates: Any) -> Optional[TopicMiningJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            for key, value in updates.items():
                setattr(job, key, value)
            job.updated_at, job.updated_ts = self._now()

            if job.status != UploadJobStatus.QUEUED.value and job.job_id in self._pending_order:
                self._pending_order.remove(job.job_id)

            return job

    def _to_public(self, job: TopicMiningJob) -> Dict[str, Any]:
        item = asdict(job)
        item.pop("owner_username", None)
        item.pop("created_ts", None)
        item.pop("updated_ts", None)
        return item

    def _trim_history_unlocked(self) -> None:
        if len(self._jobs) <= self.max_history:
            return

        active = {
            job_id
            for job_id, job in self._jobs.items()
            if job.status in {UploadJobStatus.QUEUED.value, UploadJobStatus.PROCESSING.value}
        }

        finished = [
            (job_id, job.updated_ts)
            for job_id, job in self._jobs.items()
            if job.status in {UploadJobStatus.COMPLETED.value, UploadJobStatus.FAILED.value}
        ]
        finished.sort(key=lambda item: item[1], reverse=True)

        keep_finished_count = max(0, self.max_history - len(active))
        keep_finished_ids = {job_id for job_id, _ in finished[:keep_finished_count]}
        keep = active.union(keep_finished_ids)

        for job_id in list(self._jobs.keys()):
            if job_id not in keep:
                self._jobs.pop(job_id, None)
                if job_id in self._pending_order:
                    self._pending_order.remove(job_id)


upload_jobs = UploadJobManager(doc_processor, db, vector_store, metadata_extractor)
topic_mining_jobs = TopicMiningJobManager(topic_miner, db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global db
    global mongo_client

    managed_mongo = False
    injected_database = app.state.db
    if injected_database is not None:
        db = injected_database
        upload_jobs.database = injected_database
        topic_mining_jobs.database = injected_database
    else:
        mongo_client = MongoClient(
            MONGODB_URI,
            appname=MONGODB_APP_NAME,
            serverSelectionTimeoutMS=MONGODB_SERVER_SELECTION_TIMEOUT_MS,
        )
        mongo_database = MongoDatabase(mongo_client, MONGODB_DB_NAME)
        mongo_database.ping()
        mongo_database.ensure_indexes()

        db = mongo_database
        upload_jobs.database = mongo_database
        topic_mining_jobs.database = mongo_database
        app.state.db = mongo_database
        managed_mongo = True
    upload_jobs.start()
    topic_mining_jobs.start()
    try:
        yield
    finally:
        upload_jobs.stop()
        topic_mining_jobs.stop()
        if managed_mongo:
            app.state.db = None
            db = None
            if mongo_client is not None:
                mongo_client.close()
                mongo_client = None


app = FastAPI(title="Student Study Hub RAG Chat", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.state.db = None


class ChatRequest(BaseModel):
    message: str
    selected_files: Optional[List[str]] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict]
    trace: Optional[Dict[str, Any]] = None


class AuthRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    user: Dict[str, Any]


class TagRequest(BaseModel):
    tag: str


class NoteRequest(BaseModel):
    content: str


class FolderRequest(BaseModel):
    name: str


class DocumentFolderRequest(BaseModel):
    folder_id: Optional[str] = None


class ExamFolderRequest(BaseModel):
    name: str


class ExamDocumentFolderRequest(BaseModel):
    folder_id: str


class QuizRequest(BaseModel):
    filename: str
    num_questions: int = 5
    difficulty: str = "Medium"


class FlashcardRequest(BaseModel):
    filename: str
    num_cards: int = 10


class StudySetGenerateRequest(BaseModel):
    filename: str
    type: str
    num_items: int = 10
    difficulty: str = "Medium"


class DeleteAccountRequest(BaseModel):
    username: str
    password: str


def _save_upload_file(source_file, destination: Path) -> None:
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(source_file, buffer)


def _get_owned_document_metadata(owner_username: str, filename: str) -> Dict[str, Any]:
    metadata = vector_store.get_document_metadata(owner_username, filename)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    return metadata


def _get_owned_folder(owner_username: str, folder_id: str) -> Dict[str, Any]:
    folder = _database().get_folder(owner_username, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


def _get_owned_exam_folder(owner_username: str, folder_id: str) -> Dict[str, Any]:
    folder = _database().get_exam_folder(owner_username, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Exam folder not found")
    return folder


def _get_owned_exam_document(owner_username: str, document_id: str) -> Dict[str, Any]:
    document = _database().get_exam_document(owner_username, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    return document


def _list_exam_folder_documents(owner_username: str, folder_id: str) -> List[Dict[str, Any]]:
    return [
        document
        for document in _database().list_exam_documents(owner_username)
        if document.get("folder_id") == folder_id
    ]


def _ensure_selected_files_owned(
    owner_username: str,
    selected_files: Optional[List[str]],
) -> Optional[List[str]]:
    if not selected_files:
        return None

    owned_files: List[str] = []
    for filename in selected_files:
        if not vector_store.get_document_metadata(owner_username, filename):
            raise HTTPException(status_code=404, detail=f"Document not found: {filename}")
        owned_files.append(filename)
    return owned_files


def _scrub_user_export_payload(raw_user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(raw_user, dict):
        return {}

    payload = dict(raw_user)
    payload.pop("password_hash", None)
    payload.pop("password_salt", None)

    sessions = []
    for session in payload.get("sessions", []):
        if not isinstance(session, dict):
            continue
        sessions.append(
            {
                "id": session.get("id"),
                "created_at": session.get("created_at"),
                "expires_at": session.get("expires_at"),
            }
        )
    payload["sessions"] = sessions
    return payload


def _write_json_to_zip(archive: ZipFile, archive_path: str, payload: Any) -> None:
    archive.writestr(
        archive_path,
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
    )


def _normalize_study_set_type(study_type: str) -> str:
    normalized = (study_type or "").strip().lower()
    if normalized not in ALLOWED_STUDY_SET_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported study set type")
    return normalized


def _build_study_set_record(
    generated: Dict[str, Any],
    *,
    study_type: str,
    source_filename: str,
    difficulty: str,
    model: str,
) -> Dict[str, Any]:
    items = generated.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError("Generated study set did not include items")

    return {
        "type": study_type,
        "title": generated.get("title") or "Study Set",
        "source_filename": source_filename,
        "items": items,
        "model": model,
        "difficulty": difficulty,
        "item_count": len(items),
    }


def _add_directory_to_zip(archive: ZipFile, root_path: Path, archive_root: str) -> None:
    if not root_path.exists() or not root_path.is_dir():
        return

    for path in sorted(root_path.rglob("*")):
        if path.is_file():
            relative_path = path.relative_to(root_path).as_posix()
            archive.write(path, arcname=f"{archive_root}/{relative_path}")


def _build_account_export(username: str) -> bytes:
    raw_user = _database().get_raw_user(username)
    if not raw_user:
        raise HTTPException(status_code=404, detail="User not found")

    export_buffer = BytesIO()
    export_time = datetime.now(timezone.utc)
    scrubbed_user = _scrub_user_export_payload(raw_user)
    user_root = USERS_DIR / username

    with ZipFile(export_buffer, "w", compression=ZIP_DEFLATED) as archive:
        _write_json_to_zip(
            archive,
            "manifest.json",
            {
                "app": "Study Space",
                "exported_at": export_time.isoformat(),
                "username": username,
                "version": get_frontend_asset_version(),
            },
        )
        _write_json_to_zip(
            archive,
            "account/profile.json",
            {
                "id": scrubbed_user.get("id"),
                "username": scrubbed_user.get("username"),
                "created_at": scrubbed_user.get("created_at"),
            },
        )
        _write_json_to_zip(archive, "account/sessions.json", scrubbed_user.get("sessions", []))
        _write_json_to_zip(archive, "workspace/tags.json", scrubbed_user.get("tags", []))
        _write_json_to_zip(archive, "workspace/notes.json", scrubbed_user.get("notes", []))
        _write_json_to_zip(archive, "workspace/folders.json", scrubbed_user.get("folders", []))
        _write_json_to_zip(archive, "workspace/exam_folders.json", scrubbed_user.get("exam_folders", []))
        _write_json_to_zip(
            archive,
            "workspace/exam_folder_analyses.json",
            scrubbed_user.get("exam_folder_analyses", {}),
        )
        _write_json_to_zip(archive, "workspace/document_metadata.json", scrubbed_user.get("documents", {}))
        _write_json_to_zip(archive, "workspace/exam_documents.json", scrubbed_user.get("exam_documents", {}))
        _write_json_to_zip(archive, "workspace/study_sets.json", scrubbed_user.get("study_sets", []))
        _write_json_to_zip(
            archive,
            "workspace/vector_documents.json",
            vector_store.list_all_document_metadata(username),
        )

        _add_directory_to_zip(archive, user_root / "uploads", "documents/uploads")
        _add_directory_to_zip(archive, user_root / "processed", "documents/processed")
        _add_directory_to_zip(archive, user_root / "exam_papers", "documents/exam_papers")

    export_buffer.seek(0)
    return export_buffer.getvalue()


def _delete_account_data(username: str) -> None:
    user_root = USERS_DIR / username

    vector_store.delete_user_documents(username)
    if user_root.exists():
        shutil.rmtree(user_root, ignore_errors=True)

    deleted = _database().delete_user(username)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "frontend_built": FRONTEND_ENTRY_JS.exists(),
            "frontend_asset_version": get_frontend_asset_version(),
        },
    )


@app.get("/auth/me", response_model=SessionResponse)
async def auth_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    user = _database().get_user(current_user.username)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return SessionResponse(user=user)


@app.post("/auth/signup", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def auth_signup(request: Request, response: Response, payload: AuthRequest):
    try:
        username = validate_username(payload.username)
        password = validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    password_hash, password_salt = create_password_record(password)
    try:
        user = _database().create_user(username, password_hash, password_salt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _user_upload_dir(username)
    _user_processed_dir(username)

    session_value, expires_at = create_session_for_user(_database(), username)
    _set_session_cookie(response, session_value, expires_at)
    return SessionResponse(user=user)


@app.post("/auth/signin", response_model=SessionResponse)
async def auth_signin(request: Request, response: Response, payload: AuthRequest):
    try:
        username = validate_username(payload.username)
        password = validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_record = _database().get_user_credentials(username)
    if not user_record or not verify_password(
        password,
        user_record["password_hash"],
        user_record["password_salt"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = _database().get_user(username)
    session_value, expires_at = create_session_for_user(_database(), username)
    _set_session_cookie(response, session_value, expires_at)
    return SessionResponse(user=user)


@app.post("/auth/logout")
async def auth_logout(
    request: Request,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    del current_user
    session_value = request.cookies.get(SESSION_COOKIE_NAME)
    if session_value and "." in session_value:
        session_id = session_value.split(".", 1)[0]
        _database().delete_session(session_id)
    _clear_session_cookie(response)
    return {"message": "Logged out"}


@app.get("/account/export")
async def export_account_data(current_user: AuthenticatedUser = Depends(get_current_user)):
    export_bytes = await asyncio.to_thread(_build_account_export, current_user.username)
    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"studyspace-export-{current_user.username}-{date_stamp}.zip"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(content=export_bytes, media_type="application/zip", headers=headers)


@app.delete("/account")
async def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    username = validate_username(payload.username)
    password = validate_password(payload.password)

    if current_user.username != username:
        raise HTTPException(status_code=403, detail="You can only delete your own account")

    user_record = _database().get_user_credentials(username)
    if not user_record or not verify_password(
        password,
        user_record["password_hash"],
        user_record["password_salt"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    await asyncio.to_thread(_delete_account_data, username)
    _clear_session_cookie(response)
    return {"message": "Account deleted successfully"}


@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload and enqueue a document for background processing"""
    file_path: Optional[Path] = None
    try:
        filename = os.path.basename(file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        try:
            doc_processor.ensure_supported_file(filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        storage_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = _user_upload_dir(current_user.username) / storage_name
        folder = None
        normalized_folder_id = folder_id.strip() if isinstance(folder_id, str) else None
        if normalized_folder_id:
            folder = _get_owned_folder(current_user.username, normalized_folder_id)

        await asyncio.to_thread(_save_upload_file, file.file, file_path)
        job = upload_jobs.enqueue(
            owner_username=current_user.username,
            filename=filename,
            file_path=file_path,
            folder_id=folder["id"] if folder else None,
            folder_name=folder["name"] if folder else None,
        )
        return {
            "message": f"Document '{filename}' upload accepted",
            "job": job,
        }
    except Exception as exc:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(exc)}")
    finally:
        await file.close()


@app.get("/upload-config")
async def get_upload_config(current_user: AuthenticatedUser = Depends(get_current_user)):
    del current_user
    supported_suffixes = doc_processor.get_supported_suffixes()
    return {
        "accept": ",".join(supported_suffixes),
        "supported_extensions": list(supported_suffixes),
        "supported_types_label": doc_processor.get_supported_types_label(),
    }


@app.get("/upload-jobs")
async def list_upload_jobs(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List recent upload jobs and their processing status"""
    return {"jobs": upload_jobs.list_jobs(current_user.username, limit=limit)}


@app.get("/upload-jobs/{job_id}")
async def get_upload_job(job_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get a single upload job status"""
    job = upload_jobs.get_job(current_user.username, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return job


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Handle chat requests with RAG"""
    try:
        selected_files = _ensure_selected_files_owned(current_user.username, request.selected_files)
        payload = await asyncio.to_thread(
            rag_chat.chat,
            request.message,
            current_user.username,
            selected_files,
        )
        return ChatResponse(**payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.get("/documents")
async def list_documents(current_user: AuthenticatedUser = Depends(get_current_user)):
    """List all uploaded documents"""
    return {"documents": vector_store.list_documents(current_user.username)}


@app.get("/documents/{filename}/file")
async def get_document_file(filename: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    metadata = _get_owned_document_metadata(current_user.username, filename)
    file_path = Path(metadata["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")

    media_type = "application/pdf" if filename.lower().endswith(".pdf") else None
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
    )


@app.delete("/documents/{filename}")
async def delete_document(filename: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a document"""
    try:
        metadata = _get_owned_document_metadata(current_user.username, filename)
        paths_to_delete = vector_store.get_document_paths(current_user.username, filename)

        if vector_store.delete_document(current_user.username, filename):
            for path in paths_to_delete:
                file_path = Path(path)
                if file_path.exists():
                    file_path.unlink(missing_ok=True)

            processed_path = Path(metadata["processed_path"])
            if processed_path.exists():
                processed_path.unlink(missing_ok=True)

            _database().delete_document_metadata(current_user.username, filename)

            return {"message": f"Document '{filename}' deleted successfully"}

        raise HTTPException(status_code=404, detail="Document not found in vector store")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

class DocumentTagRequest(BaseModel):
    tag: Optional[str] = None


@app.put("/documents/{filename}/tag")
async def update_document_tag(filename: str, request: DocumentTagRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Update the tag for a document"""
    try:
        # Check if doc exists
        _get_owned_document_metadata(current_user.username, filename)
        
        # Normalize and validate tag
        raw_tag = request.tag if request.tag is not None else ""
        normalized_tag = raw_tag.strip()
        
        # Treat reserved/sentinel values as "no tag"
        if normalized_tag.lower() == "uncategorized":
            normalized_tag = ""

        # Only add non-empty, non-reserved tags to the user's tag list
        if normalized_tag:
            _database().add_tag(current_user.username, normalized_tag)

        current_metadata = dict(_database().get_document_metadata(current_user.username, filename) or {})
        previous_tag = current_metadata.get("tag")
        _database().set_document_metadata(current_user.username, filename, {"tag": normalized_tag})

        success = vector_store.update_document_tag(current_user.username, filename, normalized_tag)
        if success:
            return {"message": "Document tag updated successfully", "tag": normalized_tag}
        rollback_tag = previous_tag if previous_tag is not None else ""
        _database().set_document_metadata(current_user.username, filename, {"tag": rollback_tag})
        raise HTTPException(status_code=500, detail="Failed to update document tag")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating document tag: {str(e)}")


@app.put("/documents/{filename}/folder")
async def update_document_folder(
    filename: str,
    request: DocumentFolderRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Move a document into or out of a folder."""
    try:
        _get_owned_document_metadata(current_user.username, filename)
        folder = None
        normalized_folder_id = request.folder_id.strip() if isinstance(request.folder_id, str) else None
        if normalized_folder_id:
            folder = _get_owned_folder(current_user.username, normalized_folder_id)

        previous_metadata = dict(_database().get_document_metadata(current_user.username, filename) or {})
        _database().set_document_folder(current_user.username, filename, folder["id"] if folder else None)
        success = vector_store.update_document_folder(
            current_user.username,
            filename,
            folder["id"] if folder else None,
            folder["name"] if folder else None,
        )
        if not success:
            _database().set_document_metadata(
                current_user.username,
                filename,
                {
                    "folder_id": previous_metadata.get("folder_id"),
                    "folder_name": previous_metadata.get("folder_name"),
                },
            )
            raise HTTPException(status_code=500, detail="Failed to update document folder")

        return {
            "message": "Document folder updated successfully",
            "folder_id": folder["id"] if folder else None,
            "folder_name": folder["name"] if folder else None,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating document folder: {str(e)}")


@app.get("/folders")
async def list_folders(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"folders": _database().list_folders(current_user.username)}


@app.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder(request: FolderRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        folder = _database().create_folder(current_user.username, request.name)
        return {"message": "Folder created successfully", "folder": folder}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/exam-folders")
async def list_exam_folders(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"folders": _database().list_exam_folders(current_user.username)}


@app.post("/exam-folders", status_code=status.HTTP_201_CREATED)
async def create_exam_folder(
    request: ExamFolderRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        folder = _database().create_exam_folder(current_user.username, request.name)
        return {"message": "Exam folder created successfully", "folder": folder}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/exam-folders/{folder_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_exam_folder(
    folder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    folder = _get_owned_exam_folder(current_user.username, folder_id)
    documents = _list_exam_folder_documents(current_user.username, folder_id)
    if not documents:
        raise HTTPException(status_code=400, detail="No exam papers found in this folder")

    try:
        job = topic_mining_jobs.enqueue(
            owner_username=current_user.username,
            folder_id=folder["id"],
            folder_name=folder["name"],
            total_documents=len(documents),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    analysis = _database().get_exam_folder_analysis(current_user.username, folder_id)
    return {
        "message": "Topic mining started",
        "job": job,
        "analysis": analysis,
    }


@app.get("/exam-folders/{folder_id}/analysis")
async def get_exam_folder_analysis(
    folder_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    _get_owned_exam_folder(current_user.username, folder_id)
    analysis = _database().get_exam_folder_analysis(current_user.username, folder_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No topic analysis found for this folder")
    return analysis


@app.get("/exam-papers")
async def list_exam_papers(current_user: AuthenticatedUser = Depends(get_current_user)):
    return {"documents": _database().list_exam_documents(current_user.username)}


@app.post("/exam-papers/upload", status_code=status.HTTP_201_CREATED)
async def upload_exam_paper(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    filename = os.path.basename(file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    folder = _get_owned_exam_folder(current_user.username, folder_id)
    storage_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = _user_exam_papers_dir(current_user.username) / storage_name

    try:
        await asyncio.to_thread(_save_upload_file, file.file, file_path)
        document = _database().add_exam_document(
            current_user.username,
            {
                "id": uuid.uuid4().hex,
                "filename": filename,
                "folder_id": folder["id"],
                "folder_name": folder["name"],
                "path": str(file_path),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "content_type": "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream",
            },
        )
        return {"message": "Exam paper uploaded successfully", "document": document}
    except HTTPException:
        raise
    except Exception as exc:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error uploading exam paper: {str(exc)}")
    finally:
        await file.close()


@app.put("/exam-papers/{document_id}/folder")
async def move_exam_paper(
    document_id: str,
    request: ExamDocumentFolderRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    try:
        document = _get_owned_exam_document(current_user.username, document_id)
        del document
        updated = _database().update_exam_document_folder(current_user.username, document_id, request.folder_id)
        return {
            "message": "Exam paper moved successfully",
            "document": updated,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/exam-papers/{document_id}/file")
async def get_exam_paper_file(
    document_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    document = _get_owned_exam_document(current_user.username, document_id)
    file_path = Path(document["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Exam paper file not found")

    media_type = document.get("content_type") or (
        "application/pdf" if str(document.get("filename", "")).lower().endswith(".pdf") else None
    )
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=document.get("filename"),
        content_disposition_type="inline",
    )

# Tag Endpoints
@app.get("/tags")
async def get_tags(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get all tags"""
    return {"tags": _database().get_tags(current_user.username)}


@app.post("/tags")
async def add_tag(request: TagRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Add a new tag"""
    if _database().add_tag(current_user.username, request.tag):
        return {"message": "Tag added successfully", "tag": request.tag}
    raise HTTPException(status_code=400, detail="Tag already exists")


@app.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a tag"""
    if _database().delete_tag(current_user.username, tag_name):
        return {"message": "Tag deleted successfully"}
    raise HTTPException(status_code=404, detail="Tag not found")


# Note Endpoints
@app.get("/notes")
async def get_notes(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get all notes"""
    return {"notes": _database().get_notes(current_user.username)}


@app.post("/notes")
async def add_note(request: NoteRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Add a new note"""
    note = _database().add_note(current_user.username, request.content)
    return {"message": "Note added successfully", "note": note}


@app.delete("/notes/{note_id}")
async def delete_note(note_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a note"""
    if _database().delete_note(current_user.username, note_id):
        return {"message": "Note deleted successfully"}
    raise HTTPException(status_code=404, detail="Note not found")


@app.post("/study-sets/generate")
async def generate_study_set(
    request: StudySetGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate and auto-save a study set from a document"""
    try:
        study_type = _normalize_study_set_type(request.type)
        metadata = _get_owned_document_metadata(current_user.username, request.filename)
        generated = await asyncio.to_thread(
            study_set_generator.generate_study_set,
            request.filename,
            study_type,
            request.num_items,
            request.difficulty,
            Path(metadata["processed_path"]),
        )
        study_set = _database().create_study_set(
            current_user.username,
            _build_study_set_record(
                generated,
                study_type=study_type,
                source_filename=request.filename,
                difficulty=request.difficulty,
                model=study_set_generator.model_id,
            ),
        )
        return study_set
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating study set: {str(e)}")


@app.get("/study-sets")
async def list_study_sets(current_user: AuthenticatedUser = Depends(get_current_user)):
    """List saved study sets"""
    return {"study_sets": _database().list_study_sets(current_user.username)}


@app.get("/study-sets/{study_set_id}")
async def get_study_set(study_set_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get a saved study set"""
    study_set = _database().get_study_set(current_user.username, study_set_id)
    if not study_set:
        raise HTTPException(status_code=404, detail="Study set not found")
    return study_set


@app.delete("/study-sets/{study_set_id}")
async def delete_study_set(study_set_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a saved study set"""
    if _database().delete_study_set(current_user.username, study_set_id):
        return {"message": "Study set deleted successfully"}
    raise HTTPException(status_code=404, detail="Study set not found")


@app.post("/quiz/generate")
async def generate_quiz(request: QuizRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Generate a quiz from a document"""
    try:
        metadata = _get_owned_document_metadata(current_user.username, request.filename)
        quiz = await asyncio.to_thread(
            quiz_generator.generate_quiz,
            request.filename,
            request.num_questions,
            request.difficulty,
            Path(metadata["processed_path"]),
        )
        return quiz
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")


@app.post("/flashcards/generate")
async def generate_flashcards(request: FlashcardRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Generate flashcards from a document"""
    try:
        metadata = _get_owned_document_metadata(current_user.username, request.filename)
        flashcards = await asyncio.to_thread(
            flashcard_generator.generate_flashcards,
            request.filename,
            request.num_cards,
            Path(metadata["processed_path"]),
        )
        return flashcards
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flashcards: {str(e)}")


@app.get("/metadata")
async def get_metadata(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get all extracted metadata for the user"""
    return _database().get_all_metadata(current_user.username)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
