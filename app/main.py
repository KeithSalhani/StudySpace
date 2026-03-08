"""
RAG Chat Application for Student Study Hub
"""
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from queue import Empty, Queue
from pathlib import Path
import asyncio
import logging
import os
import shutil
import threading
import time
import uuid

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
from app.db.metadata import JSONDatabase

logger = logging.getLogger(__name__)

# Check for API key
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable must be set. Please check config.py")

app = FastAPI(title="Student Study Hub RAG Chat")
FRONTEND_DIST_DIR = STATIC_DIR / "dist"
FRONTEND_ENTRY_JS = FRONTEND_DIST_DIR / "assets" / "index.js"
FRONTEND_ENTRY_CSS = FRONTEND_DIST_DIR / "assets" / "index.css"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize components
doc_processor = DocumentProcessor()
vector_store = VectorStore()
rag_chat = RAGChat(vector_store, GEMINI_API_KEY)
quiz_generator = QuizGenerator(PROCESSED_DIR, GEMINI_API_KEY)
flashcard_generator = FlashcardGenerator(PROCESSED_DIR, GEMINI_API_KEY)
db = JSONDatabase()
app.state.db = db


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
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None


class UploadJobManager:
    def __init__(
        self,
        processor: DocumentProcessor,
        database: JSONDatabase,
        store: VectorStore,
        max_history: int = 100,
    ):
        self.processor = processor
        self.database = database
        self.store = store
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

    def enqueue(self, owner_username: str, filename: str, file_path: Path) -> Dict[str, Any]:
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

            self._update_job(job_id, stage="Indexing in vector database", progress=80)
            doc_id = f"{filename}_{uuid.uuid4().hex[:8]}"
            metadata = {
                "owner_username": owner_username,
                "filename": filename,
                "path": str(file_path),
                "processed_path": str(processed_path),
                "tag": predicted_tag,
            }
            self.store.add_document(doc_id, content, metadata)

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


upload_jobs = UploadJobManager(doc_processor, db, vector_store)


class ChatRequest(BaseModel):
    message: str
    selected_files: Optional[List[str]] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict]


class AuthRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    user: Dict[str, Any]


class TagRequest(BaseModel):
    tag: str


class NoteRequest(BaseModel):
    content: str


class QuizRequest(BaseModel):
    filename: str
    num_questions: int = 5
    difficulty: str = "Medium"


class FlashcardRequest(BaseModel):
    filename: str
    num_cards: int = 10


def _save_upload_file(source_file, destination: Path) -> None:
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(source_file, buffer)


def _get_owned_document_metadata(owner_username: str, filename: str) -> Dict[str, Any]:
    metadata = vector_store.get_document_metadata(owner_username, filename)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    return metadata


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


@app.on_event("startup")
def on_startup() -> None:
    upload_jobs.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    upload_jobs.stop()


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
    user = db.get_user(current_user.username)
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
        user = db.create_user(username, password_hash, password_salt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _user_upload_dir(username)
    _user_processed_dir(username)

    session_value, expires_at = create_session_for_user(db, username)
    _set_session_cookie(response, session_value, expires_at)
    return SessionResponse(user=user)


@app.post("/auth/signin", response_model=SessionResponse)
async def auth_signin(request: Request, response: Response, payload: AuthRequest):
    try:
        username = validate_username(payload.username)
        password = validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user_record = db.get_user_credentials(username)
    if not user_record or not verify_password(
        password,
        user_record["password_hash"],
        user_record["password_salt"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = db.get_user(username)
    session_value, expires_at = create_session_for_user(db, username)
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
        db.delete_session(session_id)
    _clear_session_cookie(response)
    return {"message": "Logged out"}


@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload and enqueue a document for background processing"""
    filename = os.path.basename(file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = _user_upload_dir(current_user.username) / storage_name

    try:
        await asyncio.to_thread(_save_upload_file, file.file, file_path)
        job = upload_jobs.enqueue(
            owner_username=current_user.username,
            filename=filename,
            file_path=file_path,
        )
        return {
            "message": f"Document '{filename}' upload accepted",
            "job": job,
        }
    except Exception as exc:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(exc)}")
    finally:
        await file.close()


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
        response, sources = await asyncio.to_thread(
            rag_chat.chat,
            request.message,
            current_user.username,
            selected_files,
        )
        return ChatResponse(response=response, sources=sources)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.get("/documents")
async def list_documents(current_user: AuthenticatedUser = Depends(get_current_user)):
    """List all uploaded documents"""
    return {"documents": vector_store.list_documents(current_user.username)}


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

            return {"message": f"Document '{filename}' deleted successfully"}

        raise HTTPException(status_code=404, detail="Document not found in vector store")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


# Tag Endpoints
@app.get("/tags")
async def get_tags(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get all tags"""
    return {"tags": db.get_tags(current_user.username)}


@app.post("/tags")
async def add_tag(request: TagRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Add a new tag"""
    if db.add_tag(current_user.username, request.tag):
        return {"message": "Tag added successfully", "tag": request.tag}
    raise HTTPException(status_code=400, detail="Tag already exists")


@app.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a tag"""
    if db.delete_tag(current_user.username, tag_name):
        return {"message": "Tag deleted successfully"}
    raise HTTPException(status_code=404, detail="Tag not found")


# Note Endpoints
@app.get("/notes")
async def get_notes(current_user: AuthenticatedUser = Depends(get_current_user)):
    """Get all notes"""
    return {"notes": db.get_notes(current_user.username)}


@app.post("/notes")
async def add_note(request: NoteRequest, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Add a new note"""
    note = db.add_note(current_user.username, request.content)
    return {"message": "Note added successfully", "note": note}


@app.delete("/notes/{note_id}")
async def delete_note(note_id: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    """Delete a note"""
    if db.delete_note(current_user.username, note_id):
        return {"message": "Note deleted successfully"}
    raise HTTPException(status_code=404, detail="Note not found")


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
