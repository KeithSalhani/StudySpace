# PR Description: Migrate Structured Runtime Data From JSON To MongoDB

## Summary
This PR replaces the runtime `db.json` store with a MongoDB-backed persistence layer while keeping ChromaDB as the vector store.

The goal of this change is to move Study Space away from a single local JSON file for accounts, sessions, notes, tags, folders, and document metadata, and onto a more production-appropriate structured database design.

This PR does not replace the embedding/vector layer. ChromaDB remains responsible for chunk storage and retrieval.

## What Changed

### MongoDB Repository Layer
- Added a repository contract in `app/db/repository.py`
- Added a MongoDB implementation in `app/db/mongo.py`
- Modeled structured runtime data into Mongo collections for:
  - users
  - sessions
  - tags
  - notes
  - folders
  - documents
  - exam folder analyses
  - exam documents
- Added index creation inside the Mongo repository startup path
- Added a TTL index for session expiry

### Application Startup And Wiring
- Updated `app/main.py` to initialize MongoDB during FastAPI lifespan startup
- Added Mongo configuration in `app/config.py`:
  - `MONGODB_URI`
  - `MONGODB_DB_NAME`
  - `MONGODB_APP_NAME`
  - `MONGODB_SERVER_SELECTION_TIMEOUT_MS`
- Updated runtime wiring so `app.state.db`, the upload worker, and the topic-mining worker all use the Mongo-backed repository
- Kept the repository injectable so tests can override startup-managed Mongo when needed

### Auth And Repository Usage
- Updated `app/auth.py` to depend on the repository interface instead of the old `JSONDatabase` concrete type
- Preserved the existing session cookie format and auth flow
- Preserved current API-level behavior for signup, signin, and logout

### Data Consistency Improvements
- Tightened document metadata handling in `app/main.py`
- Tag updates now update the structured metadata store as well as Chroma metadata
- Folder updates now capture previous metadata and perform rollback if the Chroma update fails
- Upload processing now removes structured document metadata if vector indexing fails after metadata is written

### Legacy Data Migration
- Added `scripts/migrate_json_to_mongo.py`
- The migration script imports legacy `db.json` data into MongoDB
- Supported imported record types:
  - users
  - sessions
  - tags
  - notes
  - folders
  - document metadata
  - exam folder analyses
  - exam documents
- Supports `--dry-run`
- Uses upsert-style writes so reruns are safe

### Documentation
- Rewrote `README.md` to reflect the new runtime architecture
- Documented:
  - MongoDB setup
  - new environment variables
  - legacy JSON migration
  - current storage model
  - verification commands

## Why This Change
- `db.json` was acceptable for prototyping but is not a good long-term store for multi-user structured application data
- MongoDB gives us:
  - indexed lookups
  - TTL-based session cleanup
  - better separation of logical entities
  - safer concurrent access patterns
  - a cleaner path to production deployment
- This also removes the need to keep expanding one nested JSON document schema as features grow

## Scope Boundary
- MongoDB now handles the structured app data only
- ChromaDB is still the vector database
- Uploaded files and processed markdown remain on disk under `app/users/<username>/...`

## Validation
- Passed: `python3 -m compileall app scripts tests`
- Passed: `./.venv/bin/python -m pytest tests/test_auth.py tests/test_api.py -q`
- `./.venv/bin/python -m pytest tests/test_mongo_db.py -q`
  - skipped when `MONGODB_TEST_URI` is not set

## Test Coverage Added/Updated

### `tests/test_api.py`
- updated document-tag assertions so structured metadata reflects tag changes
- adjusted upload tests to stub `UploadFile.close()` directly for stable direct-handler testing
- adjusted the file-response path assertion to be compatible with the current Starlette behavior

### `tests/test_mongo_db.py`
- added Mongo integration coverage for:
  - user/session roundtrip
  - folder and document metadata persistence
  - exam-folder analysis staleness when exam papers move between folders

## Files Of Interest
- `app/db/repository.py`
- `app/db/mongo.py`
- `app/main.py`
- `scripts/migrate_json_to_mongo.py`
- `README.md`

## Commit In This Branch
- `7c03019` `Backend: migrate structured data store to MongoDB`
