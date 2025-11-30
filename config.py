"""
Configuration for the RAG Chat application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Directories
PROJECT_ROOT = Path(__file__).parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
CHROMA_DB_DIR.mkdir(exist_ok=True)

# Vector store settings
COLLECTION_NAME = "student_documents"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunk settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Search settings
DEFAULT_SEARCH_RESULTS = 3
