"""
Configuration for the RAG Chat application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "studyspace")
MONGODB_APP_NAME = os.getenv("MONGODB_APP_NAME", "studyspace-api")
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))

# Directories
PROJECT_ROOT = Path(__file__).parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"
PROCESSED_DIR = PROJECT_ROOT / "processed"
USERS_DIR = PROJECT_ROOT / "users"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)
USERS_DIR.mkdir(exist_ok=True)

# Vector store settings
COLLECTION_NAME = "student_documents"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunk settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Search settings
DEFAULT_SEARCH_RESULTS = 3

# Auth settings
SESSION_COOKIE_NAME = "studyspace_session"
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "7"))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
