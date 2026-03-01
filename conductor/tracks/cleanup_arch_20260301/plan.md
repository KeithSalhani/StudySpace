# Implementation Plan - Clean up architecture

## Phase 1: Setup and Validation
- [ ] Task: Verify current test status
    - Run existing tests (`pytest`) to establish a baseline.
- [ ] Task: Create new directory structure
    - Create `app/`, `app/core/`, `app/db/`, `app/api/`.

## Phase 2: Refactoring
- [ ] Task: Move Data Layer components
    - Move `vector_store.py` to `app/db/vector_store.py`.
    - Move `db.py` to `app/db/metadata.py`.
    - Update imports within these files.
- [ ] Task: Move Core Logic components
    - Move `rag_chat.py` to `app/core/rag.py`.
    - Move `document_processor.py` to `app/core/ingestion.py`.
    - Move `classification.py` to `app/core/classification.py`.
    - Update imports.
- [ ] Task: Move Application Entry Point
    - Move `main.py` to `app/main.py`.
    - Move `config.py` to `app/config.py`.
    - Move `templates/` and `static/` to `app/`.
    - Update all imports in `main.py` to reference `app.core` and `app.db`.

## Phase 3: Verification
- [ ] Task: Update Tests
    - Update `tests/` imports to point to new module locations.
- [ ] Task: Run Tests
    - Execute `pytest` and ensure all pass.
- [ ] Task: Manual Verification
    - Start server (`uvicorn app.main:app --reload`) and test UI.
- [ ] Task: Conductor - User Manual Verification 'Verification' (Protocol in workflow.md)
