import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.metadata import JSONDatabase


@pytest.fixture
def main_module(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")

    sys.modules.pop("app.main", None)

    doc_processor = MagicMock(name="doc_processor")
    vector_store = MagicMock(name="vector_store")
    rag_chat = MagicMock(name="rag_chat")
    quiz_generator = MagicMock(name="quiz_generator")
    flashcard_generator = MagicMock(name="flashcard_generator")
    metadata_extractor = MagicMock(name="metadata_extractor")
    topic_miner = MagicMock(name="topic_miner")
    topic_miner.model_id = "gemini-test"
    topic_miner.pipeline_version = "topic-miner-test"

    fake_ingestion = types.ModuleType("app.core.ingestion")
    fake_ingestion.DocumentProcessor = lambda: doc_processor

    fake_vector_store = types.ModuleType("app.db.vector_store")
    fake_vector_store.VectorStore = lambda: vector_store

    fake_rag = types.ModuleType("app.core.rag")
    fake_rag.RAGChat = lambda store, api_key: rag_chat

    fake_quiz = types.ModuleType("app.core.quiz_generator")
    fake_quiz.QuizGenerator = lambda processed_dir, api_key: quiz_generator

    fake_flashcards = types.ModuleType("app.core.flashcard_generator")
    fake_flashcards.FlashcardGenerator = lambda processed_dir, api_key: flashcard_generator

    fake_metadata = types.ModuleType("app.core.metadata_extractor")
    fake_metadata.MetadataExtractor = lambda api_key: metadata_extractor

    fake_topic_miner = types.ModuleType("app.core.topic_miner")
    fake_topic_miner.TopicMiner = lambda processor, api_key: topic_miner

    monkeypatch.setitem(sys.modules, "app.core.ingestion", fake_ingestion)
    monkeypatch.setitem(sys.modules, "app.db.vector_store", fake_vector_store)
    monkeypatch.setitem(sys.modules, "app.core.rag", fake_rag)
    monkeypatch.setitem(sys.modules, "app.core.quiz_generator", fake_quiz)
    monkeypatch.setitem(sys.modules, "app.core.flashcard_generator", fake_flashcards)
    monkeypatch.setitem(sys.modules, "app.core.metadata_extractor", fake_metadata)
    monkeypatch.setitem(sys.modules, "app.core.topic_miner", fake_topic_miner)

    imported = importlib.import_module("app.main")

    async def immediate_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    imported.asyncio.to_thread = immediate_to_thread

    imported.USERS_DIR = tmp_path / "users"
    imported.USERS_DIR.mkdir(parents=True, exist_ok=True)

    test_db = JSONDatabase(str(tmp_path / "test_db.json"))
    imported.db = test_db
    imported.app.state.db = test_db
    imported.upload_jobs.database = test_db
    imported.topic_mining_jobs.database = test_db

    yield imported

    imported.upload_jobs.stop()
    imported.topic_mining_jobs.stop()
    sys.modules.pop("app.main", None)


@pytest.fixture
def client(main_module):
    with TestClient(main_module.app) as test_client:
        yield test_client
