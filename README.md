# Study Space

Study Space is a FastAPI + React study assistant for document-grounded chat, quizzes, flashcards, notes, and topic tagging. Users sign up with a username and password, upload their own study material, and interact only with data that belongs to their account.

## What It Does

- Upload PDF, DOCX, TXT, and Markdown study documents
- Process and classify uploaded documents into topic tags
- Ask questions against your own indexed material with RAG
- Generate quizzes and flashcards from a selected document
- Save personal notes and manage personal tags
- Keep each user’s documents, notes, sessions, and retrieval results isolated

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- Vector search: ChromaDB
- Embeddings: `all-MiniLM-L6-v2`
- LLM features: Google Gemini via `google-genai`
- Metadata store: local JSON file

## Authentication And Isolation

### Login model

- Accounts are stored in `db.json` through `app/db/metadata.py`.
- Passwords are stored as PBKDF2 hashes with per-user salts. The hashing and session helpers live in `app/auth.py`.
- Successful sign-in/sign-up issues an `HttpOnly` session cookie named `studyspace_session`.
- Sessions are validated server-side on every protected request.

### How user data is separated

- Notes and tags are stored per user in `db.json`.
- Uploaded source files are stored under `app/users/<username>/uploads/`.
- Processed Markdown files are stored under `app/users/<username>/processed/`.
- Upload job history is kept in memory but filtered per authenticated user before being returned.
- ChromaDB is currently shared physically but segregated logically:
  - one persistent Chroma database directory
  - one shared collection
  - every stored chunk includes `owner_username`
  - every search, list, metadata lookup, and delete path filters on `owner_username`

That means users do not get a separate Chroma database right now. Isolation is enforced through ownership metadata and mandatory filters in the vector-store layer.

## Storage Layout

Current generated storage paths:

```text
app/chroma_db/              Shared Chroma persistence
app/users/<username>/uploads/
app/users/<username>/processed/
db.json                     User accounts, sessions, notes, tags
```

Legacy root-level generated directories such as `uploads/`, `processed/`, and `chroma_db/` are obsolete and should not be used.

## Project Structure

```text
.
├── app/
│   ├── auth.py
│   ├── config.py
│   ├── main.py
│   ├── core/
│   │   ├── classification.py
│   │   ├── flashcard_generator.py
│   │   ├── ingestion.py
│   │   ├── quiz_generator.py
│   │   └── rag.py
│   ├── db/
│   │   ├── metadata.py
│   │   └── vector_store.py
│   ├── static/
│   ├── templates/
│   └── users/
├── frontend/
├── tests/
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites

- Python 3.12 recommended
- Node.js for the frontend build
- A valid `GEMINI_API_KEY`

### Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

### Configure

Set the Gemini key in your environment or `.env`:

```bash
export GEMINI_API_KEY="your_key_here"
```

Optional auth-related env vars:

```bash
SESSION_TTL_DAYS=7
SESSION_COOKIE_SECURE=false
```

## Run

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`, create an account, then upload documents and use the workspace.

## Main API Routes

Auth:

- `POST /auth/signup`
- `POST /auth/signin`
- `POST /auth/logout`
- `GET /auth/me`

Workspace:

- `POST /upload`
- `GET /upload-jobs`
- `GET /upload-jobs/{job_id}`
- `POST /chat`
- `GET /documents`
- `DELETE /documents/{filename}`
- `GET/POST/DELETE /tags`
- `GET/POST/DELETE /notes`
- `POST /quiz/generate`
- `POST /flashcards/generate`

All workspace routes require an authenticated session.

## Verification

Useful commands:

```bash
./venv/bin/python -m pytest tests
./venv/bin/python -m coverage erase
./venv/bin/python -m coverage run --source=app -m pytest tests
./venv/bin/python -m coverage report -m
cd frontend && npm run build
```

Notes:

- Use `--source=app` when running coverage so the report is limited to the application code and avoids errors from synthetic modules created by some dependencies.
- If you want coverage for only the app code total, the last line of `coverage report -m` shows the overall percentage.

## Notes

- Chroma isolation is currently logical, not physical. If you want stronger tenant isolation, the next step is per-user collections or per-user Chroma directories.
- The repo still has some compatibility constants for old shared upload/processed paths, but active document storage is user-scoped under `app/users/`.
