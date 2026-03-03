"""
RAG Chat Application for Student Study Hub
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query, status
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

from app.config import GEMINI_API_KEY, UPLOAD_DIR, STATIC_DIR, TEMPLATES_DIR, PROCESSED_DIR
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


class UploadJobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UploadJob:
    job_id: str
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

    def enqueue(self, filename: str, file_path: Path) -> Dict[str, Any]:
        now, now_ts = self._now()
        job = UploadJob(
            job_id=uuid.uuid4().hex,
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

    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_ts, reverse=True)
            if limit > 0:
                jobs = jobs[:limit]
            return [self._to_public(job) for job in jobs]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
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
            content = self.processor.process_document(str(file_path))

            self._update_job(job_id, stage="Saving processed file", progress=35)
            processed_path = PROCESSED_DIR / f"{filename}.md"
            with open(processed_path, "w", encoding="utf-8") as out_file:
                out_file.write(content)

            self._update_job(job_id, stage="Classifying document", progress=55)
            current_tags = self.database.get_tags()
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
                self.database.add_tag(predicted_tag)

            self._update_job(job_id, stage="Indexing in vector database", progress=80)
            doc_id = f"{filename}_{uuid.uuid4().hex[:8]}"
            metadata = {
                "filename": filename,
                "path": str(file_path),
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


@app.on_event("startup")
def on_startup() -> None:
    upload_jobs.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    upload_jobs.stop()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(file: UploadFile = File(...)):
    """Upload and enqueue a document for background processing"""
    filename = os.path.basename(file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = UPLOAD_DIR / storage_name

    try:
        await asyncio.to_thread(_save_upload_file, file.file, file_path)
        job = upload_jobs.enqueue(filename=filename, file_path=file_path)
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
async def list_upload_jobs(limit: int = Query(default=25, ge=1, le=100)):
    """List recent upload jobs and their processing status"""
    return {"jobs": upload_jobs.list_jobs(limit=limit)}


@app.get("/upload-jobs/{job_id}")
async def get_upload_job(job_id: str):
    """Get a single upload job status"""
    job = upload_jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return job


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with RAG"""
    try:
        response, sources = await asyncio.to_thread(rag_chat.chat, request.message, request.selected_files)
        return ChatResponse(response=response, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    return {"documents": vector_store.list_documents()}


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document"""
    try:
        paths_to_delete = vector_store.get_document_paths(filename)

        if vector_store.delete_document(filename):
            for path in paths_to_delete:
                file_path = Path(path)
                if file_path.exists():
                    file_path.unlink(missing_ok=True)

            processed_path = PROCESSED_DIR / f"{filename}.md"
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
async def get_tags():
    """Get all tags"""
    return {"tags": db.get_tags()}


@app.post("/tags")
async def add_tag(request: TagRequest):
    """Add a new tag"""
    if db.add_tag(request.tag):
        return {"message": "Tag added successfully", "tag": request.tag}
    raise HTTPException(status_code=400, detail="Tag already exists")


@app.delete("/tags/{tag_name}")
async def delete_tag(tag_name: str):
    """Delete a tag"""
    if db.delete_tag(tag_name):
        return {"message": "Tag deleted successfully"}
    raise HTTPException(status_code=404, detail="Tag not found")


# Note Endpoints
@app.get("/notes")
async def get_notes():
    """Get all notes"""
    return {"notes": db.get_notes()}


@app.post("/notes")
async def add_note(request: NoteRequest):
    """Add a new note"""
    note = db.add_note(request.content)
    return {"message": "Note added successfully", "note": note}


@app.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    """Delete a note"""
    if db.delete_note(note_id):
        return {"message": "Note deleted successfully"}
    raise HTTPException(status_code=404, detail="Note not found")


@app.post("/quiz/generate")
async def generate_quiz(request: QuizRequest):
    """Generate a quiz from a document"""
    try:
        quiz = await asyncio.to_thread(
            quiz_generator.generate_quiz,
            request.filename,
            request.num_questions,
            request.difficulty,
        )
        return quiz
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")


@app.post("/flashcards/generate")
async def generate_flashcards(request: FlashcardRequest):
    """Generate flashcards from a document"""
    try:
        flashcards = await asyncio.to_thread(
            flashcard_generator.generate_flashcards,
            request.filename,
            request.num_cards,
        )
        return flashcards
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flashcards: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
