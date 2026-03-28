# PR Description: More Agentic RAG With Compact Workspace Catalog And Search Modes

## Summary
This PR makes the chat retrieval flow more agentic without inflating prompt size.

The new flow is:
1. build a compact, user-scoped workspace catalog from indexed files
2. give that catalog to the planner up front
3. let the model choose how each step should search:
   - `unfocused`
   - `focused`
   - `full_document`
4. execute the chosen search plan against only the current user's documents
5. answer from fused chunk evidence and/or direct full-document context

The goal is to handle requests like:
- questions about a module tag such as `Security`
- questions about multiple exact files at once
- requests to compare specific exam papers directly

## Backend Changes

### `app/core/workspace_catalog.py`
Added a compact workspace-catalog builder designed to be token-light enough for planner prompts.

Output shape:

```json
{
  "tags": {
    "Security": ["23-24.pdf", "lec-01.pdf"],
    "Exam Papers": ["18-19.pdf", "19-20.pdf"]
  },
  "untagged_files": ["misc.pdf"]
}
```

Important constraints:
- the catalog is built only from `vector_store.list_documents(owner_username)`
- it contains only indexed, searchable documents
- it does not include topic-miner exam workspace data
- it strips noisy metadata and keeps only what the planner needs

### `app/core/rag.py`
`RAGChat` now uses the compact catalog as part of planning and execution.

Added:
- `_build_workspace_catalog(...)`
- `_get_catalog_files(...)`
- `_infer_target_files(...)`
- `_normalize_target_files(...)`
- `_normalize_search_mode(...)`
- `_execute_search_plan(...)`
- `_fetch_full_document_sources(...)`

Planner changes:
- `_generate_query_plan(...)` now passes the workspace catalog to Gemini
- planner output can now include:
  - `search_mode`
  - `module_tag`
  - `target_files`
- `_normalize_query_plan(...)` validates:
  - exact tags only from the catalog
  - exact filenames only from the catalog
  - duplicate search steps removed

Supported search modes:
- `unfocused`
  - broad chunk search
- `focused`
  - chunk search narrowed by exact file(s), exact tag, or both
- `full_document`
  - direct full-document reads for named files before answer generation

Execution changes:
- focused file targeting now works with `selected_files`
- direct full-document planning no longer waits for fallback logic
- planned full-document reads and fallback full-document reads now share one fetch path

Trace changes:
- planned steps now expose:
  - `search_mode`
  - `module_tag`
  - `target_files`
- full-document fetch trace now includes:
  - `query_id`
  - `search_mode`

## Behavior Change

### Previous behavior
- planner only chose query text plus an optional tag
- retrieval was always chunk search
- full-document reads happened only as a fallback after chunk review
- planner had no compact view of exact user file/tag structure

### New behavior
- planner sees a compact tag-to-files map for the current user
- planner can choose exact file targets immediately
- planner can decide straight away whether a step should be:
  - broad
  - narrowed
  - direct full-document
- exact named files can bypass chunk retrieval when that is the better strategy

## Frontend Changes

### `frontend/src/App.jsx`
The retrieval trace UI now surfaces planner intent much more clearly.

Added:
- explicit search-mode labels for:
  - `Broad search`
  - `Focused search`
  - `Direct document read`
  - `Fallback document read`
- exact `target_files` pills on planned and executed steps
- clearer executed-step rendering for `full_document` plans
- updated loading copy so the in-flight state reflects mode selection rather than fixed query generation wording

Also fixed a runtime rendering bug in the trace header:
- removed a direct `React.Fragment` usage from a file using the automatic JSX runtime
- this resolves the `ReferenceError: React is not defined` crash that caused the chat view to disappear after a response

### `frontend/src/styles.css`
Added styling for the new trace affordances:
- search-mode pills
- target-file pills
- compact chip rows for plan and execution cards

## User Isolation
This PR keeps retrieval localized to the requesting user.

Isolation still holds because:
- the catalog is built from `vector_store.list_documents(owner_username)`
- chunk search still applies `owner_username` filtering in the vector store
- full-document reads still call `get_full_document_content(owner_username, filename)`
- file selection still goes through the existing ownership checks in the API layer

## Why This Architecture
- The planner gets just enough structure to reason about tags and exact files without wasting tokens.
- The model can choose the retrieval strategy instead of forcing everything through chunk search first.
- Exact-file comparisons become much more reliable when the model can request direct full-document reads.
- The approach preserves the existing trace contract while making the retrieval decisions more explicit.

## Validation
- Passed: `./venv/bin/python -m pytest tests/test_rag_chat.py tests/test_workspace_catalog.py -q`
- Passed: `./venv/bin/python -m pytest tests/test_api.py -k chat_endpoint_with_selected_files_scoped_to_user -q`
- Passed: `python -m py_compile app/core/rag.py app/core/workspace_catalog.py`
- Passed: `npm run build` in `frontend/`

Note:
- There is an unrelated existing local failure in `tests/test_api.py::test_get_document_file_returns_owned_file` caused by an assertion comparing `Path` vs `str`. This PR does not change that path.

## Test Updates

### `tests/test_workspace_catalog.py`
Added coverage for:
- compact tag-map output
- untagged file handling
- user scoping of the catalog builder

### `tests/test_rag_chat.py`
Added and updated coverage for:
- planner steps with `search_mode`
- exact file targeting
- direct full-document execution
- full-document trace metadata

## Commit Breakdown
- `d87522f` `RAG: add compact user-scoped workspace catalog`
- `953b1c5` `RAG: let planner choose search mode and exact file targets`
- `6db8277` `RAG: execute focused and full-document retrieval plans`
- pending frontend commit for clearer trace mode visibility and runtime fix

## Follow-Up Work
- add an explicit max-planned-steps / max-tool-calls budget to the planner trace
- consider normalizing tag labels such as `Artifical Intelligence` if that typo exists in persisted user data
