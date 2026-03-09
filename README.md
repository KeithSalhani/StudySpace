# Study Space

Study Space is a FastAPI + React study assistant for document-grounded chat, quizzes, flashcards, notes, and topic tagging. Users sign up with a username and password, upload their own study material, and interact only with data that belongs to their account.

## What It Does

- **Document Ingestion**: Upload PDF, DOCX, TXT, and Markdown study documents.
- **Automated Processing**: Extract text, chunk documents, and classify uploaded documents into topic tags.
- **RAG Chat**: Ask questions against your own indexed material using Retrieval-Augmented Generation (RAG).
- **Study Aids**: Generate quizzes and flashcards directly from a selected document.
- **Personal Workspace**: Save personal notes and manage custom topic tags.
- **Data Privacy**: Keep each user’s documents, notes, sessions, and retrieval results fully isolated.

## Why It Exists

Study Space was built to provide students and lifelong learners with a private, intelligent workspace. By combining traditional study tools (notes, flashcards, tags) with advanced AI capabilities (document summarization, RAG-based Q&A, automatic quiz generation), it aims to streamline the learning process while ensuring that users' study materials remain segregated and private.

## Architecture and Internal Workings

The project is built on a modern, decoupled architecture:

- **Frontend**: React application built with Vite (`frontend/`).
- **Backend**: FastAPI serving REST endpoints and managing background tasks (`app/`).
- **Storage & State**:
  - **Vector Store**: ChromaDB is used for storing document embeddings and performing similarity searches for RAG. While physically shared, it is logically segregated; every stored chunk includes an `owner_username` metadata field, and all queries are filtered by this field.
  - **Metadata & User Data**: A local JSON file (`db.json`) acts as the database for user accounts, sessions, notes, and tags.
  - **File Storage**: Uploaded source files and processed Markdown files are stored locally under user-specific directories (`app/users/<username>/`).
- **AI Integration**:
  - **Embeddings**: `all-MiniLM-L6-v2` via `sentence-transformers` for creating vector representations of document chunks.
  - **LLM Features**: Google's Gemini (`gemini-3.1-flash-lite-preview`) is integrated using the `google-genai` SDK to power the chat, quiz generation, and flashcard generation features.
  - **Classification**: Zero-shot classification is used during document ingestion to automatically assign tags to uploaded content.

### Execution Flow (Document Upload)

1. A user uploads a document via the frontend.
2. The FastAPI backend receives the file and saves it to the user's `uploads` directory.
3. An `UploadJob` is enqueued and processed by a background worker thread (`app/main.py`).
4. The background worker uses `DocumentProcessor` to extract text from the file (converting it to Markdown).
5. The extracted text is classified to predict a relevant tag.
6. The text is chunked, embedded, and stored in ChromaDB by the `VectorStore`.
7. The processed Markdown is saved in the user's `processed` directory.

## Repository Structure

```text
.
├── app/                        # FastAPI Backend
│   ├── api/                    # (Future API route modules)
│   ├── core/                   # Core business logic
│   │   ├── classification.py   # Zero-shot classification
│   │   ├── flashcard_generator.py # LLM-based flashcard generation
│   │   ├── ingestion.py        # Document text extraction (MarkItDown)
│   │   ├── quiz_generator.py   # LLM-based quiz generation
│   │   └── rag.py              # RAG Chat logic integrating Gemini
│   ├── db/                     # Data access layer
│   │   ├── metadata.py         # JSON-based storage for users, notes, tags
│   │   └── vector_store.py     # ChromaDB wrapper
│   ├── static/                 # Static assets (including built frontend)
│   ├── templates/              # Jinja2 templates (index.html)
│   ├── users/                  # User data storage (uploads & processed files)
│   ├── auth.py                 # Authentication, password hashing, sessions
│   ├── config.py               # Environment configuration
│   └── main.py                 # FastAPI application entry point & routes
├── frontend/                   # React Frontend
│   ├── src/                    # React components and logic
│   ├── package.json            # Node.js dependencies
│   └── vite.config.js          # Vite build configuration
├── tests/                      # Pytest suite
├── requirements.txt            # Python backend dependencies
├── README.md                   # This file
└── README_TESTS.md             # Testing documentation
```

## Setup & Development

### Prerequisites

- Python 3.12+ recommended
- Node.js (for the frontend build)
- A valid Google Gemini API Key (`GEMINI_API_KEY`)

### Backend Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Set the required API key in your environment or a `.env` file in the root directory:
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"
   ```
   *Optional Configuration:*
   ```bash
   export SESSION_TTL_DAYS=7
   export SESSION_COOKIE_SECURE=false
   ```

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Build the frontend:**
   The backend expects the compiled frontend to be in the `app/static/dist` folder.
   ```bash
   npm run build
   ```

### Running the Application

From the root directory, start the FastAPI server with live reloading:

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`. You can create an account, log in, and begin uploading documents.

### Deployment

For production deployment, you should:
1. Run Uvicorn without the `--reload` flag.
2. Consider running Uvicorn behind a reverse proxy like Nginx or using Gunicorn with Uvicorn workers.
3. Ensure `SESSION_COOKIE_SECURE` is set to `true` if serving over HTTPS.
4. Use a more robust, persistent storage solution for `db.json` if scaling horizontally (though local JSON works for single-instance deployments).

## Testing

The project uses `pytest` for backend unit and integration tests. See `README_TESTS.md` for full details.

To run the test suite, ensure your virtual environment is active and run:

```bash
pip install pytest
python -m pytest tests/
```

*Note: The frontend currently relies on Vite's build process; specific frontend unit tests can be added in the `frontend/` directory.*

## Main API Endpoints

The FastAPI backend exposes the following key REST endpoints. Most endpoints require a valid session cookie obtained via login.

### Authentication
- `POST /auth/signup`: Create a new user account.
- `POST /auth/signin`: Authenticate and receive an `HttpOnly` session cookie.
- `POST /auth/logout`: Invalidate the current session.
- `GET /auth/me`: Retrieve current user details.

### Workspace (Requires Authentication)
- `POST /upload`: Upload a document (enqueues a background job).
- `GET /upload-jobs`: List recent upload processing jobs.
- `GET /upload-jobs/{job_id}`: Check the status of a specific job.
- `GET /documents`: List all processed documents belonging to the user.
- `DELETE /documents/{filename}`: Delete a document and its embeddings.
- `POST /chat`: Submit a message to the RAG system (optionally filtering by `selected_files`).
- `GET / POST / DELETE /tags`: Manage custom user tags.
- `GET / POST / DELETE /notes`: Manage user notes.
- `POST /quiz/generate`: Generate a quiz from a specific document.
- `POST /flashcards/generate`: Generate flashcards from a specific document.

## Operational Details

### Data Isolation
All user data is strictly isolated. `db.json` separates notes and tags by username. Files are stored in `app/users/<username>/`. ChromaDB uses a single shared collection, but all queries, inserts, and deletions enforce a metadata filter: `{"owner_username": "<username>"}`.

### Logging and Error Handling
The backend uses Python's standard `logging` module. Logs are currently output to standard out (console) and detail server startup, background worker progress (e.g., "Extracting text", "Indexing in vector database"), and error stack traces.
If an upload job fails during background processing, its status is updated to `Failed`, the error message is stored in the job history, and temporary files are cleaned up where possible.

### Security
- **Passwords**: Hashed using PBKDF2 with per-user salts (`app/auth.py`).
- **Sessions**: Managed via secure, `HttpOnly` cookies.
- **API Keys**: External API keys (like Gemini) are managed via environment variables and are never exposed to the frontend.

## Contributor Guidance

Contributions are welcome! Please follow these steps:
1. Fork the repository and create a feature branch.
2. Ensure you have the full development environment set up.
3. Write clear, documented code adhering to the existing style.
4. Run the full test suite (`python -m pytest tests/`) to ensure no regressions.
5. Submit a pull request detailing your changes and the problem they solve.
