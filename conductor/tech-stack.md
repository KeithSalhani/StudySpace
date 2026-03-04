# Technology Stack: StudySpace

## Core Application
*   **Language:** Python 3.8+
*   **Backend Framework:** FastAPI (High-performance async web framework)
*   **Server:** Uvicorn (ASGI implementation)
*   **Frontend:** Jinja2 Templates (Server-side rendering) + Vanilla JavaScript (Interactive elements)

## AI & Machine Learning
*   **Large Language Model (LLM):** Google Gemini 2.0 Flash (via `google-genai` SDK)
*   **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (Local, CPU-friendly)
*   **Zero-Shot Classification:** `facebook/bart-large-mnli` (via `transformers` pipeline)
*   **Document Parsing:** Docling (IBM) for advanced PDF/layout analysis and OCR.

## Data Storage
*   **Vector Database:** ChromaDB (Local persistence)
*   **Metadata Store:**
    *   *Current:* JSON (`db.json`) for tags and simple notes.
    *   *Planned:* SQLite (via `aiosqlite` or SQLAlchemy) for relational data like quizzes/deadlines.

## Infrastructure & Tooling
*   **Package Management:** `pip` / `requirements.txt`
*   **Version Control:** Git
*   **Environment:** `.env` for secrets (API Keys)
*   **Testing:** `pytest` (Backend logic), `httpx` (API integration)
*   **Deployment:** Docker (Planned for hosted version)