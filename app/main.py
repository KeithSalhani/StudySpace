"""
RAG Chat Application for Student Study Hub
"""

from contextlib import asynccontextmanager
from typing import Optional

import asyncio
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient

from app.api.deps import build_app_services, set_runtime_context
from app.api.routers import (
    account_router,
    auth_router,
    chat_router,
    documents_router,
    exams_router,
    study_router,
    ui_router,
    uploads_router,
    workspace_router,
)
from app.api.routers.account import delete_account, export_account_data
from app.api.routers.auth import auth_logout, auth_me, auth_signin, auth_signup
from app.api.routers.chat import chat
from app.api.routers.documents import (
    create_folder,
    delete_document,
    delete_metadata_entry,
    get_document_file,
    list_documents,
    list_folders,
    update_document_folder,
    update_document_tag,
)
from app.api.routers.exams import (
    analyze_exam_folder,
    create_exam_folder,
    get_exam_folder_analysis,
    get_exam_paper_file,
    list_exam_folders,
    list_exam_papers,
    move_exam_paper,
    upload_exam_paper,
)
from app.api.routers.study import (
    delete_study_set,
    generate_flashcards,
    generate_quiz,
    generate_study_set,
    get_study_set,
    list_study_sets,
)
from app.api.routers.ui import home
from app.api.routers.uploads import get_upload_config, get_upload_job, list_upload_jobs, upload_document
from app.api.routers.workspace import add_note, add_tag, delete_note, delete_tag, get_metadata, get_notes, get_tags
from app.api.schemas import (
    AuthRequest,
    ChatRequest,
    ChatResponse,
    DeleteAccountRequest,
    DocumentFolderRequest,
    DocumentTagRequest,
    ExamDocumentFolderRequest,
    ExamFolderRequest,
    FlashcardRequest,
    FolderRequest,
    NoteRequest,
    QuizRequest,
    SessionResponse,
    StudySetGenerateRequest,
    TagRequest,
)
from app.auth import create_password_record
from app.config import (
    GEMINI_API_KEY,
    MONGODB_APP_NAME,
    MONGODB_DB_NAME,
    MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    MONGODB_URI,
    STATIC_DIR,
    USERS_DIR,
)
from app.db.mongo import MongoDatabase
from app.db.repository import DatabaseRepository
from app.services.frontend import FRONTEND_ENTRY_CSS, FRONTEND_ENTRY_JS
from app.services.jobs import TopicMiningJob, TopicMiningJobManager, UploadJob, UploadJobManager, UploadJobStatus
from app.services.ownership import ensure_selected_files_owned
from app.services.storage import (
    save_upload_file as _save_upload_file,
    user_exam_papers_dir as _user_exam_papers_dir,
    user_processed_dir as _user_processed_dir,
    user_root as _user_root,
    user_upload_dir as _user_upload_dir,
)

logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable must be set. Please check config.py")

services = build_app_services()
doc_processor = services.doc_processor
vector_store = services.vector_store
rag_chat = services.rag_chat
quiz_generator = services.quiz_generator
flashcard_generator = services.flashcard_generator
study_set_generator = services.study_set_generator
metadata_extractor = services.metadata_extractor
topic_miner = services.topic_miner
upload_jobs = UploadJobManager(doc_processor, None, vector_store, metadata_extractor)
topic_mining_jobs = TopicMiningJobManager(topic_miner, None)
services.upload_jobs = upload_jobs
services.topic_mining_jobs = topic_mining_jobs

db: Optional[DatabaseRepository] = None
mongo_client: Optional[MongoClient] = None


def get_frontend_asset_version() -> str:
    timestamps = []
    for path in (FRONTEND_ENTRY_JS, FRONTEND_ENTRY_CSS):
        if path.exists():
            timestamps.append(str(int(path.stat().st_mtime)))
    return "-".join(timestamps) if timestamps else "dev"


def _ensure_selected_files_owned(owner_username: str, selected_files):
    return ensure_selected_files_owned(vector_store, owner_username, selected_files)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

    app.state.services = services
    set_runtime_context(app.state.db, services)
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
        set_runtime_context(app.state.db, services)


app = FastAPI(title="Student Study Hub RAG Chat", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.state.db = None
app.state.services = services
set_runtime_context(app.state.db, services)

for router in (
    ui_router,
    auth_router,
    account_router,
    uploads_router,
    chat_router,
    documents_router,
    exams_router,
    workspace_router,
    study_router,
):
    app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
