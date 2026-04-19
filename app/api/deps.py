from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import GEMINI_API_KEY, PROCESSED_DIR, TEMPLATES_DIR
from app.core.flashcard_generator import FlashcardGenerator
from app.core.ingestion import DocumentProcessor
from app.core.metadata_extractor import MetadataExtractor
from app.core.quiz_generator import QuizGenerator
from app.core.rag import RAGChat
from app.core.study_set_generator import StudySetGenerator
from app.core.topic_miner import TopicMiner
from app.db.repository import DatabaseRepository
from app.db.vector_store import VectorStore


@dataclass
class AppServices:
    doc_processor: DocumentProcessor
    vector_store: VectorStore
    rag_chat: RAGChat
    quiz_generator: QuizGenerator
    flashcard_generator: FlashcardGenerator
    study_set_generator: StudySetGenerator
    metadata_extractor: MetadataExtractor
    topic_miner: TopicMiner
    templates: Jinja2Templates
    upload_jobs: object | None = None
    topic_mining_jobs: object | None = None


_fallback_db: Optional[DatabaseRepository] = None
_fallback_services: Optional[AppServices] = None


def build_app_services() -> AppServices:
    doc_processor = DocumentProcessor()
    vector_store = VectorStore()
    return AppServices(
        doc_processor=doc_processor,
        vector_store=vector_store,
        rag_chat=RAGChat(vector_store, GEMINI_API_KEY),
        quiz_generator=QuizGenerator(PROCESSED_DIR, GEMINI_API_KEY),
        flashcard_generator=FlashcardGenerator(PROCESSED_DIR, GEMINI_API_KEY),
        study_set_generator=StudySetGenerator(PROCESSED_DIR, GEMINI_API_KEY),
        metadata_extractor=MetadataExtractor(GEMINI_API_KEY),
        topic_miner=TopicMiner(doc_processor, GEMINI_API_KEY),
        templates=Jinja2Templates(directory=str(TEMPLATES_DIR)),
    )


def set_runtime_context(
    database: Optional[DatabaseRepository],
    services: Optional[AppServices],
) -> None:
    global _fallback_db
    global _fallback_services
    _fallback_db = database
    _fallback_services = services


def get_db(request: Request | None = None) -> DatabaseRepository:
    if request is not None and hasattr(request, "app"):
        database = getattr(request.app.state, "db", None)
        if database is not None:
            return database
    if _fallback_db is None:
        raise RuntimeError("Database is not initialized")
    return _fallback_db


def get_services(request: Request | None = None) -> AppServices:
    if request is not None and hasattr(request, "app"):
        services = getattr(request.app.state, "services", None)
        if services is not None:
            return services
    if _fallback_services is None:
        raise RuntimeError("Application services are not initialized")
    return _fallback_services


def get_db_dependency(request: Request) -> DatabaseRepository:
    return get_db(request)


def get_services_dependency(request: Request) -> AppServices:
    return get_services(request)
