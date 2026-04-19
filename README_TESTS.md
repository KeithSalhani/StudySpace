# Study Space Testing Guide

This repository uses:

- `pytest` for backend and unit/integration tests
- `coverage.py` for Python line coverage
- Playwright for frontend browser E2E coverage

The authoritative local Python environment is `./.venv`.

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

That install now includes the test runner and coverage tooling.

## Run The Suite

Run the full test suite:

```bash
./.venv/bin/python -m pytest tests
```

Run a single test file:

```bash
./.venv/bin/python -m pytest tests/test_api.py
```

Run a single test case:

```bash
./.venv/bin/python -m pytest tests/test_auth.py -k login
```

Using `python -m pytest` keeps imports aligned with the active project interpreter.

## Frontend E2E

Frontend E2E coverage lives in `frontend/e2e/` and uses Playwright.

Run the browser suite:

```bash
cd frontend
npm run test:e2e
```

Run it headed for debugging:

```bash
cd frontend
npm run test:e2e:headed
```

The Playwright setup:

- starts a local Vite dev server automatically
- uses mocked same-origin API responses for the covered flows
- keeps the E2E suite deterministic without requiring the full backend stack

Current browser flows include:

- authentication sign-in/sign-out
- chat submission against selected documents
- saved study-set generation flow
- document upload and delete flow
- topic tag creation and deletion
- note creation and deletion
- accessibility settings toggles

## Coverage

Measure coverage for application code under `app/`:

```bash
./.venv/bin/python -m coverage erase
./.venv/bin/python -m coverage run --source=app -m pytest tests
./.venv/bin/python -m coverage report -m
```

Why `--source=app` is used:

- It reports coverage for the application code rather than tests or site-packages.
- It keeps the total percentage focused on the shipped backend code.

## Test Inventory

The current suite is split across the current modular codebase:

### API and app wiring

- `tests/test_api.py`: API-level behavior for backend endpoints and study workflows.
- `tests/test_auth.py`: authentication and validation behavior.
- `tests/test_main.py`: FastAPI app entrypoint behavior and app wiring.

These map most directly to the assembled FastAPI app in `app/main.py` and the routed HTTP layer in `app/api/routers/`.

### Core logic and services

- `tests/test_classification.py`: document classification helpers.
- `tests/test_demo.py`: demo-oriented RAG behavior.
- `tests/test_document_processor.py`: ingestion and document processing behavior.
- `tests/test_flashcard_generator.py`: flashcard generation logic.
- `tests/test_metadata_extractor.py`: metadata extraction flows.
- `tests/test_quiz_generator.py`: quiz generation logic.
- `tests/test_rag_chat.py`: RAG orchestration and response handling.
- `tests/test_study_set_generator.py`: saved study-set generation and normalization behavior.
- `tests/test_topic_miner.py`: topic miner normalization, fallback, and analysis helper behavior.
- `tests/test_workspace_catalog.py`: workspace catalog construction and filtering.

These primarily cover the modular backend logic under `app/core/` and the supporting service behavior those flows depend on.

### Persistence and integration

- `tests/test_db.py`: database-facing behavior outside Mongo integration tests.
- `tests/test_mongo_db.py`: MongoDB integration coverage.
- `tests/test_vector_store.py`: vector store indexing and retrieval behavior.

These cover the persistence layer under `app/db/`, including Mongo-backed records and Chroma retrieval behavior.

Shared fixtures and test helpers live in `tests/conftest.py`.

### Frontend E2E

Frontend browser coverage lives under `frontend/e2e/` and exercises the modular React app in `frontend/src/app/`.

Playwright specs:

- `frontend/e2e/auth.spec.js`: sign-in and logout flow.
- `frontend/e2e/chat.spec.js`: chat interaction flow with grounded response rendering.
- `frontend/e2e/study-sets.spec.js`: study-set generation and practice modal flow.
- `frontend/e2e/workspace-management.spec.js`: upload/delete, tags, notes, and accessibility settings flows.

Mocked API responses for these flows live in `frontend/e2e/support/mockApi.js`.

## Environment Notes

- Most tests are designed to run locally with the Python dependencies from `requirements.txt`.
- Mongo integration tests in `tests/test_mongo_db.py` require `MONGODB_TEST_URI`.
- Some features in the application depend on services or secrets such as MongoDB and `GEMINI_API_KEY`, but much of the suite uses mocks so the full app stack is not required for every test file.

Example Mongo test run:

```bash
MONGODB_TEST_URI="mongodb://localhost:27017" ./.venv/bin/python -m pytest tests/test_mongo_db.py
```

## Practical Workflow

For normal development, this is the useful minimum:

```bash
./.venv/bin/python -m pytest tests
./.venv/bin/python -m coverage run --source=app -m pytest tests
./.venv/bin/python -m coverage report -m
cd frontend && npm run test:e2e
```

If coverage or test collection fails immediately, verify that you are using `./.venv/bin/python` and that `pip install -r requirements.txt` completed successfully in that same environment.
