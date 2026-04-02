# Study Space

Study Space is a FastAPI + React study workspace for user-scoped document chat, revision tools, and exam-paper analysis. Users can upload their own material, organize it into folders, generate quizzes and flashcards, chat against indexed documents with a transparent retrieval trace, and analyze folders of exam papers in the Topic Miner workspace.

## Features

- Upload PDF, DOCX, TXT, and Markdown study documents
- User-scoped RAG chat over uploaded material
- Transparent chat trace showing generated queries, retrieval runs, and fused evidence
- Automatic document tagging with editable tags
- Folder organization for study documents
- Quiz and flashcard generation from selected documents
- Personal notes and tags
- Background upload job tracking
- Calendar/workspace views for extracted academic events
- Topic Miner workspace for exam-paper analysis across multiple PDFs
- Inline owned-file viewing for study documents and exam papers
- Accessibility settings including voice input, higher contrast, larger text, reduced motion, and stronger focus states

## Architecture

- Frontend: React + Vite, built into backend-served static assets
- Backend: FastAPI in [`app/main.py`](app/main.py)
- Structured app data: MongoDB through [`app/db/mongo.py`](app/db/mongo.py)
- Repository contract: [`app/db/repository.py`](app/db/repository.py)
- Vector store: ChromaDB in [`app/db/vector_store.py`](app/db/vector_store.py)
- Embeddings: `all-MiniLM-L6-v2`
- LLM features: Google Gemini via `google-genai`
- Ingestion and metadata extraction: [`app/core/ingestion.py`](app/core/ingestion.py), [`app/core/metadata_extractor.py`](app/core/metadata_extractor.py)
- Exam topic mining: [`app/core/topic_miner.py`](app/core/topic_miner.py)

## Data Model

MongoDB stores the structured runtime data:

- users
- sessions
- tags
- notes
- folders
- documents
- exam folder analyses
- exam documents

ChromaDB stores chunked document embeddings and retrieval metadata.

## Authentication And Isolation

- Users sign up and sign in with username + password.
- Passwords are stored as PBKDF2 hashes with per-user salts in [`app/auth.py`](app/auth.py).
- Successful auth issues an `HttpOnly` cookie named `studyspace_session`.
- Session settings come from [`app/config.py`](app/config.py) via `SESSION_TTL_DAYS` and `SESSION_COOKIE_SECURE`.

User data is isolated as follows:

- MongoDB records are scoped by user identity.
- Study documents are stored under `app/users/<username>/uploads/`.
- Processed Markdown is stored under `app/users/<username>/processed/`.
- Exam papers are stored under `app/users/<username>/exam_papers/`.
- ChromaDB is physically shared, but every indexed chunk stores `owner_username`.
- Search, metadata lookup, folder assignment, tag updates, file fetches, and deletes are scoped by authenticated user.

## Storage Layout

```text
app/chroma_db/                      Shared Chroma persistence
app/static/dist/                    Built frontend assets
app/users/<username>/uploads/       Uploaded study documents
app/users/<username>/processed/     Processed markdown for study documents
app/users/<username>/exam_papers/   Uploaded exam papers
MongoDB                             Structured runtime data
```

Legacy `db.json` is not used at runtime anymore. It is only relevant if you need to import old data into MongoDB.

## Setup

### Prerequisites

- Python 3.12 recommended
- Node.js
- A valid `GEMINI_API_KEY`
- A reachable MongoDB instance

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

### Configure

Set required environment variables in your shell or `.env`:

```bash
export GEMINI_API_KEY="your_key_here"
export MONGODB_URI="mongodb://localhost:27017"
export MONGODB_DB_NAME="studyspace"
```

Optional settings:

```bash
export SESSION_TTL_DAYS=7
export SESSION_COOKIE_SECURE=false
export MONGODB_APP_NAME=studyspace-api
export MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
```

### Run

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`, create an account, and use the workspace.

## Migrating Legacy `db.json`

If you have legacy JSON-backed data, import it into MongoDB with:

```bash
python scripts/migrate_json_to_mongo.py \
  --json-path db.json \
  --mongo-uri "$MONGODB_URI" \
  --db-name "$MONGODB_DB_NAME"
```

Preview counts without writing:

```bash
python scripts/migrate_json_to_mongo.py \
  --json-path db.json \
  --mongo-uri "$MONGODB_URI" \
  --db-name "$MONGODB_DB_NAME" \
  --dry-run
```

The importer upserts users, sessions, tags, notes, folders, document metadata, exam analyses, and exam documents. When rerun for the same usernames, it preserves any existing Mongo user ID for that username and reuses it for related imported records.

## Topic Miner

Topic Miner is the exam-paper analysis workspace. It does not reuse the normal study-document upload flow.

Current flow:

1. Create dedicated exam folders.
2. Upload exam PDFs into those folders.
3. Run folder-level analysis.
4. Gemini extracts topic structure from each paper.
5. Folder-level recurring themes and example questions are synthesized and saved.
6. Saved analyses are reopened later and marked stale when folder contents change.

## Chat Flow

The chat pipeline in [`app/core/rag.py`](app/core/rag.py) is a retrieval-planned RAG flow rather than a single search:

1. The user sends a message to `POST /chat`.
2. The backend builds a compact catalog from the user’s visible documents.
3. Gemini produces a small retrieval plan.
4. Retrieval runs execute against Chroma by step.
5. Chunks are fused and deduplicated.
6. Gemini answers from the fused evidence set.
7. The API returns `response`, `sources`, and `trace`.
8. The frontend renders the trace inline.

## API Surface

### Auth

- `POST /auth/signup`
- `POST /auth/signin`
- `POST /auth/logout`
- `GET /auth/me`

### Study Workspace

- `POST /upload`
- `GET /upload-jobs`
- `GET /upload-jobs/{job_id}`
- `POST /chat`
- `GET /documents`
- `GET /documents/{filename}/file`
- `DELETE /documents/{filename}`
- `PUT /documents/{filename}/tag`
- `PUT /documents/{filename}/folder`
- `GET /folders`
- `POST /folders`
- `GET /tags`
- `POST /tags`
- `DELETE /tags/{tag_name}`
- `GET /notes`
- `POST /notes`
- `DELETE /notes/{note_id}`
- `POST /quiz/generate`
- `POST /flashcards/generate`
- `GET /metadata`

### Topic Miner / Exam Papers

- `GET /exam-folders`
- `POST /exam-folders`
- `POST /exam-folders/{folder_id}/analyze`
- `GET /exam-folders/{folder_id}/analysis`
- `GET /exam-papers`
- `POST /exam-papers/upload`
- `PUT /exam-papers/{document_id}/folder`
- `GET /exam-papers/{document_id}/file`

## Verification

Useful commands:

```bash
./.venv/bin/python -m pytest tests/test_auth.py tests/test_api.py
./.venv/bin/python -m pytest tests/test_mongo_db.py
./.venv/bin/python -m coverage run --source=app -m pytest tests
cd frontend && npm run build
```

Notes:

- `tests/test_mongo_db.py` requires `MONGODB_TEST_URI` and skips otherwise.
- ChromaDB remains the vector store in the current implementation; MongoDB replaces the old JSON-backed structured store only.
