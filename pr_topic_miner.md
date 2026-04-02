# PR Description: Topic Miner Workspace And Gemini-Powered Exam Theme Analysis

## Overview
This PR introduces the first full Topic Miner workflow as a separate exam-paper workspace inside Study Space. It splits exam papers away from the main document/RAG workspace, adds folder-based PDF management for past papers, and builds a Gemini-powered topic-mining pipeline that analyzes exam folders and surfaces recurring themes.

At a high level, the new flow is:
1. create dedicated exam folders inside Topic Miner
2. upload PDFs directly into those folders without sending them through the main ingestion pipeline
3. preview papers inside the Topic Miner workspace
4. run folder analysis from the Topic Miner UI
5. send the actual exam PDFs to Gemini for per-paper topic extraction
6. synthesize recurring themes across the folder and persist the result for later viewing

## Backend Changes

### Separate Exam Paper Storage
Topic Miner now uses its own exam-specific persistence layer rather than the main workspace document flow.

Changes in [metadata.py](/home/horsehead/Projects/StudySpace_Interim/app/db/metadata.py):
- added `exam_folders`
- added `exam_documents`
- added `exam_folder_analyses`
- added helpers for:
  - listing and creating exam folders
  - storing and moving exam documents between exam folders
  - saving and loading per-folder analysis results
  - marking saved analyses as stale when papers are uploaded or moved

Changes in [main.py](/home/horsehead/Projects/StudySpace_Interim/app/main.py):
- added exam-only endpoints:
  - `GET /exam-folders`
  - `POST /exam-folders`
  - `GET /exam-papers`
  - `POST /exam-papers/upload`
  - `PUT /exam-papers/{document_id}/folder`
  - `GET /exam-papers/{document_id}/file`
- exam-paper uploads do not go through the main workspace `/upload` path
- exam-paper file responses are served inline for browser preview rather than download

This keeps Topic Miner isolated from the normal study document workflow and avoids unnecessary transcription/classification for uploaded exam papers.

### Gemini Topic Mining Pipeline
Added a new Topic Miner service in [topic_miner.py](/home/horsehead/Projects/StudySpace_Interim/app/core/topic_miner.py).

The pipeline uses a 2-pass structure:
- pass 1: analyze each paper individually and extract Questions 1-4 into structured JSON
- pass 2: synthesize recurring themes across all extracted papers in the folder

Important implementation detail:
- PDFs are now sent to Gemini as actual `application/pdf` inputs
- smaller files are sent inline as PDF bytes
- larger files fall back to Gemini file upload handling
- non-PDF documents still have a plain-text fallback path

Returned paper-level data includes:
- paper title
- year
- question number
- canonical topic
- subtopic
- question summary
- evidence quote
- confidence

Folder-level synthesis returns:
- canonical themes
- question positions where they recur
- recurrence counts across papers
- recurring subtopics
- example questions
- optional observations

### Background Analysis Jobs
Added a dedicated Topic Miner background job manager in [main.py](/home/horsehead/Projects/StudySpace_Interim/app/main.py).

New behavior:
- folder analysis is queued and processed asynchronously
- progress, stage, completion, and failure states are persisted per folder
- completed results are stored and reloaded later instead of re-running Gemini every time the UI opens

New endpoints:
- `POST /exam-folders/{folder_id}/analyze`
- `GET /exam-folders/{folder_id}/analysis`

This gives Topic Miner a stable backend contract:
- start analysis
- poll/load analysis state
- reopen completed analysis later

### Vector Store Safety Improvement
Updated [vector_store.py](/home/horsehead/Projects/StudySpace_Interim/app/db/vector_store.py) to normalize metadata into Chroma-compatible scalar values before insertion or update.

This change:
- removes `None` values
- preserves scalar metadata directly
- serializes nested metadata into JSON strings when needed

This is not Topic Miner-specific, but it landed in the same branch and improves resilience around metadata writes.

## Frontend Changes

### Topic Miner Workspace
Reworked [TopicMinerWorkspace.jsx](/home/horsehead/Projects/StudySpace_Interim/frontend/src/TopicMinerWorkspace.jsx) into a dedicated full-screen exam workspace.

The layout now supports:
- left-side exam folder navigation
- second-stage paper list for the selected folder
- first-page PDF previews inside the paper list
- full PDF preview in the main panel
- direct folder analysis controls
- saved analysis rendering in the main panel when no PDF is selected

Folder interactions now include:
- create folder
- upload PDF to selected folder
- move papers between folders
- analyze folder
- re-run folder analysis
- explicitly reopen analysis with `View analysis` / `Open`

### Analysis UI
Added frontend API methods in [api.js](/home/horsehead/Projects/StudySpace_Interim/frontend/src/api.js):
- `analyzeExamFolder(...)`
- `getExamFolderAnalysis(...)`

The Topic Miner UI now:
- starts analysis from the folder or papers pane
- shows queued/processing/completed/failed analysis state
- polls active folder analyses while they are running
- renders saved theme results in the main panel
- shows summary stats:
  - papers
  - questions
  - themes
  - stale/current status
- renders:
  - observations
  - canonical themes
  - recurring subtopics
  - example questions

### UI Stability Fixes
Adjusted [App.jsx](/home/horsehead/Projects/StudySpace_Interim/frontend/src/App.jsx), [TopicMinerWorkspace.jsx](/home/horsehead/Projects/StudySpace_Interim/frontend/src/TopicMinerWorkspace.jsx), and [styles.css](/home/horsehead/Projects/StudySpace_Interim/frontend/src/styles.css) to fix workflow problems discovered during iteration.

Notable fixes:
- stabilized the Topic Miner fetch path so upload-job polling in the parent app no longer retriggers exam-folder and exam-paper fetches continuously
- ensured the upload action and analysis actions wrap correctly instead of being pushed off-screen
- added explicit analysis reopen controls so completed analysis does not disappear behind PDF preview state
- improved collapsed/open panel behavior and analysis/paper switching

## Why This Architecture
- Exam-paper analysis is conceptually separate from the main study workspace, so it should not reuse the general upload-and-transcribe path
- Long-context Gemini is a better fit for “what keeps recurring in exam papers?” than heavyweight topic-modeling infrastructure for this use case
- A 2-pass structured JSON pipeline is much easier to render, cache, and debug than a single large prose response
- Saving folder analyses makes the feature feel like a workspace tool rather than a one-shot prompt
- Background jobs keep the UI responsive and make progress/state handling straightforward

## Validation
- Passed: `python -m py_compile app/core/topic_miner.py app/db/metadata.py app/main.py tests/conftest.py tests/test_api.py tests/test_db.py`
- Passed: `npm run build` in `frontend/`

Could not run:
- `pytest` in this environment, because `pytest` was not installed in either the system Python or the local `.venv`

## Test Updates

### `tests/conftest.py`
- added Topic Miner service mocking to the existing FastAPI test harness

### `tests/test_api.py`
- added coverage for:
  - starting exam-folder analysis
  - reading saved exam-folder analysis payloads

### `tests/test_db.py`
- added coverage for:
  - attaching analysis summaries to folder listings
  - marking folder analyses stale when papers are added or moved

### `tests/test_vector_store.py`
- added coverage for metadata sanitization in vector store writes

## Commits In This Branch
- `3d3c406` `Backend: add separate exam paper folders and file endpoints`
- `79c215d` `UI: build separate exam paper workspace in topic miner`
- `de89954` `Backend: add Gemini topic mining pipeline for exam folders`
- `9f25a5b` `UI: add topic miner analysis workspace flow`
- `777d8cd` `Backend: refine vector store metadata handling`

## Follow-Up Work
- improve prompt quality for year extraction and more reliable question segmentation
- add a lightweight verification pass on Gemini outputs before saving final folder themes
- consider adding generated thumbnails for PDF cards instead of relying on inline first-page iframes
- decide whether completed analyses should support version history instead of simple stale/current state
