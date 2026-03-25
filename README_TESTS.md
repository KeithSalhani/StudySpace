# StudySpace Testing Guide

This document outlines the testing infrastructure for the StudySpace project. The project uses `pytest` for unit and integration testing, and `coverage.py` for line coverage reporting.

## Test Structure

The tests are located in the `tests/` directory and mirror the application structure:

- `tests/test_document_processor.py`: Tests for document ingestion, text extraction, and classification integration.
- `tests/test_classification.py`: Tests for the zero-shot classification logic and text truncation.
- `tests/test_vector_store.py`: Tests for the ChromaDB integration, embedding generation, and document chunking.
- `tests/test_rag_chat.py`: Tests for the RAG pipeline, prompt engineering, and LLM interaction (mocked).
- `tests/test_db.py`: Tests for the JSON database (tags and notes management).

## Running Tests

### Prerequisites

Ensure you have the required test dependencies installed (these are in addition to the main `requirements.txt`):

```bash
pip install pytest coverage
```

### Execution

To run the full test suite, execute the following command from the project root:

```bash
./venv/bin/python -m pytest tests
```

*Note: Using `python -m pytest` ensures that the current directory is added to the Python path, preventing import errors.*

### Coverage

To measure application coverage only, run:

```bash
./venv/bin/python -m coverage erase
./venv/bin/python -m coverage run --source=app -m pytest tests
./venv/bin/python -m coverage report -m
```

Why `--source=app` matters:

- It limits coverage reporting to the project application code.
- It avoids report failures caused by synthetic or dependency-generated modules that do not exist as normal source files.

## Test Descriptions

### 1. Document Processor (`test_document_processor.py`)
Verifies that:
- Documents are correctly processed using `MarkItDown`.
- Text files are read correctly.
- The classifier is correctly invoked with the extracted text.
- Error handling works for missing files.

### 2. Classification (`test_classification.py`)
Verifies that:
- The `Classifier` class correctly interfaces with the Hugging Face pipeline.
- Text inputs longer than the model's limit are safely truncated.
- Classification results are returned in the expected format.

### 3. Vector Store (`test_vector_store.py`)
Verifies that:
- Documents are properly split into chunks (sliding window).
- Embeddings are generated (mocked).
- Documents are added to and deleted from ChromaDB.
- Search queries return the expected results structure.

### 4. RAG Chat (`test_rag_chat.py`)
Verifies that:
- The chat engine correctly retrieves context from the vector store.
- Prompts are constructed correctly (with and without context).
- The LLM response is processed and returned with citations.
- Empty responses from the LLM are handled gracefully.

### 5. Database (`test_db.py`)
Verifies that:
- The JSON database file is created if it doesn't exist.
- Tags can be added, retrieved, and deleted.
- Notes can be created, stored, and removed.
- Duplicate tags are prevented.

## Continuous Integration

These tests should be run before any commit to ensure no regressions are introduced.
