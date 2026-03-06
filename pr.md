# PR Description: feat(rag): Support scoped search by selecting specific documents

## Overview
This PR implements a Scoped Search feature, allowing users to restrict AI queries to specific documents or modules. The RAG system now supports filtering the knowledge base context via a new document selection sidebar in the UI.

## Key Changes

### Backend (API & Core)
- Updated `app/core/rag.py` and `app/db/vector_store.py` to support an optional `selected_files` filter.
- Implemented a metadata filter in ChromaDB search logic using the `$in` operator to scope retrieval to selected filenames.
- Updated the `/chat` endpoint in `app/main.py` to accept a `selected_files` list in the request body.

### Frontend (UI/UX)
- Added a document list to the sidebar with checkboxes for each file.
- Configured documents to be selected by default to maintain global search as the standard behavior.
- Updated the chat submission logic to collect checked file states and include them in the API request payload.

## Testing & Verification

### Automated Tests
- Updated `tests/test_rag_chat.py` to verify that the retrieval system correctly applies metadata filters.
- Created `tests/test_api.py` to ensure the `/chat` endpoint correctly parses the file selection payload.

### Manual Verification
1. Verified that uploaded documents appear in the sidebar with checkboxes.
2. Confirmed that deselecting specific documents limits the AI's response and citations to the remaining selected files.
3. Verified that global search remains functional when all files are selected.
