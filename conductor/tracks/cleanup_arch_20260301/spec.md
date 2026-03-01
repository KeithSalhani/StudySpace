# Track Specification: Clean up architecture

## Objective
Refactor the current flat file structure into a modular, scalable architecture as described in the System Design (Section 4.4). The goal is to separate concerns (Presentation, Application, Data) and improve maintainability.

## Current State
All files are in the root directory:
- `main.py`
- `rag_chat.py`
- `vector_store.py`
- `document_processor.py`
- `classification.py`
- `config.py`
- `db.py`
- `db.json`

## Target Architecture
```
/app
    ├── __init__.py
    ├── main.py                 # Application Entry Point
    ├── config.py               # Configuration
    ├── api/                    # API Routes (Future expansion)
    ├── core/                   # Core Logic
    │   ├── rag.py              # (rag_chat.py)
    │   ├── ingestion.py        # (document_processor.py)
    │   └── classification.py   # (classification.py)
    ├── db/                     # Data Access Layer
    │   ├── vector_store.py     # (vector_store.py)
    │   └── metadata.py         # (db.py)
    └── templates/              # Jinja2 Templates (Moved from root)
    └── static/                 # Static Assets (Moved from root)
```

## Requirements
1.  **Move Files**: Relocate Python files to `app/` and subdirectories.
2.  **Update Imports**: Fix all import statements in `main.py` and modules to reflect new structure.
3.  **Update Config**: Ensure paths (e.g., to `chroma_db`, `uploads`) are correctly resolved relative to the new structure or project root.
4.  **Verify Functionality**: Ensure the application still starts and tests pass.

## Constraints
-   Do not change business logic, only structure.
-   Ensure `requirements.txt` remains valid.
