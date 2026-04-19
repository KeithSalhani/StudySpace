from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

import logging
import threading
import time
import uuid

from app.core.ingestion import DocumentProcessor
from app.core.metadata_extractor import MetadataExtractor
from app.core.topic_miner import TopicMiner
from app.db.repository import DatabaseRepository
from app.db.vector_store import VectorStore
from app.services.storage import user_processed_dir

logger = logging.getLogger(__name__)


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
            jobs = [job for job in self._jobs.values() if job.owner_username == owner_username]
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
            processed_path = user_processed_dir(owner_username) / f"{uuid.uuid4().hex}_{filename}.md"
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
