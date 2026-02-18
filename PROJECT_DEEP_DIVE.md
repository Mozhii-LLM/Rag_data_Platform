# Mozhii Platform Deep Dive

This document explains the full project in a teachable, implementation-level way:
- Why it exists
- How each layer works
- How data moves through every stage
- What each important function does
- How frontend and backend are connected
- What to watch out for while extending the code

---

## 1) What this project is

Mozhii Platform is a workflow system for preparing RAG training/retrieval data.

It is not an LLM chat app. It is a data pipeline UI and API where humans prepare content in 3 stages:
1. Raw collection
2. Cleaning
3. Chunking

Each stage has review gates:
- Submission goes to pending
- Admin approves/rejects/edits
- Approved data is stored separately
- Approved data can be pushed to HuggingFace dataset repos

---

## 2) Tech stack and design choices

### Backend
- Python Flask
- Blueprint routing modularization
- Local file-based storage (text and JSON metadata)
- HuggingFace Hub API integration

### Frontend
- Server-rendered HTML (single page with tabs)
- Vanilla JavaScript modules
- CSS-based component styling

### Why this architecture
- Simple to run locally
- Low dependency complexity
- Transparent file-level auditability
- Easy to inspect pending/approved content in plain files

Tradeoff:
- Local file system persistence means deployment must support persistent storage.

---

## 3) High-level component map

- Entry point: run.py
- Flask app factory: app/__init__.py
- Config: app/config.py
- Routes:
  - app/routes/main.py
  - app/routes/raw_data.py
  - app/routes/cleaning.py
  - app/routes/chunking.py
  - app/routes/admin.py
- Services:
  - app/services/huggingface.py
  - app/services/storage.py (mostly scaffold, not primary route path currently)
- Data schemas:
  - app/models/schemas.py
- Frontend:
  - templates/index.html
  - static/js/main.js
  - static/js/raw-data.js
  - static/js/cleaning.js
  - static/js/chunking.js

---

## 4) Boot flow: from process start to browser ready

## 4.1 run.py

Main steps:
1. Load .env values via dotenv
2. Call create_app() from app package
3. Read DEBUG and PORT env vars
4. Start Flask server on 0.0.0.0:PORT

Key idea:
- run.py is only startup wiring; most logic is in app package.

## 4.2 app/__init__.py create_app(config_name=None)

This is the factory pattern.

Function behavior:
1. Build Flask instance with template and static folders
2. Load Config object
3. Enable CORS
4. Ensure data folder tree exists
5. Register route blueprints with URL prefixes
6. Return configured app instance

Blueprint URL prefixes:
- main: /
- raw: /api/raw
- cleaning: /api/cleaning
- chunking: /api/chunking
- admin: /api/admin

---

## 5) Configuration system

File: app/config.py

Config class centralizes:
- Flask core settings: SECRET_KEY, DEBUG
- HF credentials/repo names
- Storage directory absolute paths
- Admin defaults
- Supported languages/categories/source types

Important operational detail:
- Path constants resolve from project root, so file I/O stays stable regardless of where process starts.

---

## 6) Data storage model in detail

Data is split by stage and moderation status.

Directory layout:
- data/pending/raw
- data/pending/cleaned
- data/pending/chunked
- data/approved/raw
- data/approved/cleaned
- data/approved/chunked

For raw/cleaned item:
- content file: filename.txt
- metadata file: filename.meta.json

For chunked item:
- folder per source file
- chunk JSON files like chunk_01.json

Why this model works:
- Human readable
- Easy admin operations (move/delete)
- Version-like trail in metadata fields

---

## 7) API and frontend integration model

Frontend calls backend using fetch through one wrapper function in static/js/main.js.

General request pattern:
1. User action triggers handler in tab JS file
2. Handler validates form state
3. Handler calls api(endpoint, options)
4. Flask route processes request
5. Route writes/reads files and returns JSON
6. Frontend shows toast and refreshes affected lists

This is straightforward request-response; no websockets or background queue.

---

## 8) Main routes explained function by function

File: app/routes/main.py

### index()
- Route: GET /
- Returns index.html
- This is the application shell page

### health_check()
- Route: GET /health
- Returns service status, version, platform fields
- Useful for uptime probes and deployment checks

### get_config()
- Route: GET /api/config
- Returns safe client config (languages, categories, sourceTypes, repo names)
- Does not expose secret tokens

---

## 9) Raw data routes explained function by function

File: app/routes/raw_data.py

### generate_metadata(filename, language, source, content)
- Utility function
- Creates metadata object with id, timestamps, status, lengths

### submit_raw_data()
- Route: POST /api/raw/submit
- Validates required fields: filename, language, source, content
- Validates filename pattern
- Rejects duplicate pending filename
- Writes:
  - pending/raw/filename.txt
  - pending/raw/filename.meta.json
- Returns submission id and success status

### list_pending()
- Route: GET /api/raw/pending
- Reads all .meta.json files from pending raw
- Sorts newest first by submitted_at

### list_approved()
- Route: GET /api/raw/approved
- Reads all .meta.json from approved raw
- Sorts newest first by approved_at

### get_file_content(filename)
- Route: GET /api/raw/file/<filename>
- Checks pending first, then approved
- Returns content + metadata + location

---

## 10) Cleaning routes explained function by function

File: app/routes/cleaning.py

### list_raw_files()
- Route: GET /api/cleaning/raw-files
- Reads approved raw files only (important lineage rule)
- Includes preview and full content for cleaning UI
- Derives cleaning status by checking pending/approved cleaned files

### submit_cleaned_data()
- Route: POST /api/cleaning/submit
- Requires filename and cleaned content
- Verifies source raw file exists in approved raw
- Loads original metadata to preserve language/source/lineage
- Writes pending cleaned content + metadata

### list_pending()
- Route: GET /api/cleaning/pending
- Lists pending cleaned metadata

### list_approved()
- Route: GET /api/cleaning/approved
- Lists approved cleaned metadata

### get_file_content(filename)
- Route: GET /api/cleaning/file/<filename>
- Returns pending or approved cleaned content and metadata

---

## 11) Chunking routes explained function by function

File: app/routes/chunking.py

### generate_chunk_id(language, category, filename, index)
- Utility for stable chunk id format
- Combines language, short category, short filename, index

### list_cleaned_files()
- Route: GET /api/chunking/cleaned-files
- Lists approved cleaned files as chunk sources
- Includes counts of pending and approved chunks

### get_chunks(filename)
- Route: GET /api/chunking/chunks/<filename>
- Reads pending and approved chunk json files
- Adds status field per chunk
- Sorts by chunk_index

### submit_chunk()
- Route: POST /api/chunking/submit
- Validates required fields: filename, text, category
- Verifies source cleaned file exists
- Computes next chunk index from existing pending+approved count
- Generates chunk object and writes pending chunk json file

### submit_batch()
- Route: POST /api/chunking/submit-batch
- Accepts array of chunk payloads for same file
- Computes sequential indices
- Writes multiple pending chunk files

### list_pending()
- Route: GET /api/chunking/pending
- Returns pending chunks grouped by source filename

### delete_chunk(filename, chunk_index)
- Route: DELETE /api/chunking/chunk/<filename>/<chunk_index>
- Deletes pending chunk only

---

## 12) Admin routes explained function by function

File: app/routes/admin.py

### get_all_pending()
- Route: GET /api/admin/pending
- Aggregates pending items across raw/cleaned/chunked
- Returns per-stage arrays and total counters

### get_pending_item()
- Route: GET /api/admin/item
- Query params: type, filename, optional chunk_index
- Returns a specific pending item's content for edit flow

### update_pending_item()
- Route: POST /api/admin/update
- Updates pending content/metadata/chunk data
- Adds updated_at and updated_by audit fields

### approve_submission()
- Route: POST /api/admin/approve
- For raw/cleaned: move files from pending to approved and update metadata
- For chunk: move chunk file to approved folder and update chunk status fields

### reject_submission()
- Route: POST /api/admin/reject
- Deletes pending item (or specific chunk)
- Logs rejection with reason

### approve_all()
- Route: POST /api/admin/approve-all
- Bulk approval by type:
  - raw all
  - cleaned all
  - chunks for one filename

### get_stats()
- Route: GET /api/admin/stats
- Returns pending/approved counts for each stage + totals

### push_to_huggingface()
- Route: POST /api/admin/push-to-hf
- Requires type and HF token (from body or env)
- Iterates approved data and uploads via HuggingFaceService
- Returns per-stage upload/failure counts

---

## 13) Frontend HTML structure and behavior

File: templates/index.html

Main UI blocks:
- Header + admin panel toggle
- Tab nav for raw, cleaning, chunking
- Tab panel sections with forms and list panes
- Admin sidebar for queue and HuggingFace push inputs
- Generic toast container
- Generic modal

Script load order:
1. main.js
2. raw-data.js
3. cleaning.js
4. chunking.js

Implication:
- Shared helpers from main.js are available to tab modules.

---

## 14) Frontend shared engine functions

File: static/js/main.js

### AppState object
Global in-memory state for current tab, config, pending counters.

### api(endpoint, options)
- Wrapper around fetch
- Sets json headers
- Parses response json
- Throws standardized errors on non-2xx

### showToast(title, message, type, duration)
- Creates and inserts toast UI
- Auto-removes with timer

### showModal(title, content, buttons)
- Generic modal renderer with dynamic footer actions

### hideModal()
- Hides modal overlay

### initTabs()
- Handles tab button click
- Switches active panel
- Triggers stage refresh for cleaning/chunking tabs

### initAdminSidebar()
- Handles open/close of sidebar
- Triggers admin data refresh on open

### refreshAdminData()
- Calls /api/admin/pending and /api/admin/stats
- Updates badge/stats and pending lists

### renderPendingList(containerId, items, type)
- Renders pending raw/cleaned item rows with edit/approve/reject actions

### renderPendingChunks(containerId, chunkedFiles)
- Renders grouped pending chunks and approve-all action

### approveItem(type, filename)
- Calls /api/admin/approve then refreshes UI

### rejectItem(type, filename)
- Confirms in modal then calls /api/admin/reject

### approveAllChunks(filename)
- Calls /api/admin/approve-all with type chunks

### editItem(type, filename)
- Active definition (later in file) uses:
  - GET /api/admin/item?type=...&filename=...
  - POST /api/admin/update
- Opens modal, allows editing content, saves update

### pushToHuggingFace()
- Active definition (later in file) uses token/repo from sidebar inputs
- Calls /api/admin/push-to-hf with type all
- Displays upload result summary modal

### initHFConfig()
- Binds sync button
- Loads/saves token and repo to localStorage

### initModalHandlers()
- Adds close handlers: close button, overlay click, Escape key

### loadConfig()
- Fetches /api/config and stores AppState.config

### DOMContentLoaded initializer
- Calls loadConfig
- Initializes tabs, sidebar, modals, hf config
- Refreshes admin badge data

Important code quality note:
- main.js includes duplicate definitions for some functions (editItem, pushToHuggingFace, initHFConfig).
- JavaScript uses the last definition encountered, so the later versions are active at runtime.

---

## 15) Raw tab frontend functions

File: static/js/raw-data.js

### RawDataElements.init()
Caches dom elements for raw form controls.

### validateFilename(filename)
Checks required, regex pattern, min and max length.

### validateContent(content)
Checks required and min content length.

### validateRawDataForm()
Runs filename/content validations and returns aggregate result.

### updateCharCount()
Live character count and short-content warning style.

### handleRawDataSubmit()
- Validates form
- Disables submit button
- POST /api/raw/submit
- On success: toast, clear form, refresh admin data
- Re-enables button finally

### clearRawDataForm()
Resets fields to defaults and focuses filename input.

### initRawDataEventListeners()
Wires input, click, blur/focus, and Ctrl+Enter handlers.

### DOMContentLoaded
Initializes element cache, listeners, and char count.

---

## 16) Cleaning tab frontend functions

File: static/js/cleaning.js

### CleaningElements.init()
Caches cleaning pane dom nodes.

### CleaningState
Holds file list, selected file, selected raw content.

### refreshCleaningFiles()
Calls /api/cleaning/raw-files and updates list.

### renderCleaningFileList()
Renders clickable file cards with cleaning status.

### formatStatus(status)
Maps internal status values to user-facing labels.

### selectCleaningFile(filename)
Selects file, fills raw preview, enables controls, clears cleaned textarea.

### escapeHtml(text)
Prevents html injection in preview.

### copyRawContent()
Copies selected raw content to clipboard with feedback.

### updateCleaningCharCount()
Live cleaned text character count.

### clearCleaningForm()
Clears cleaned textarea.

### handleCleaningSubmit()
- Validates selected file and content
- POST /api/cleaning/submit
- On success: toast + refresh lists + refresh admin badge

### initCleaningEventListeners()
Binds refresh/copy/clear/submit/input/shortcut events.

### DOMContentLoaded
Initializes dom refs and event listeners.

---

## 17) Chunking tab frontend functions

File: static/js/chunking.js

### ChunkingElements.init()
Caches dom elements for chunking screen.

### ChunkingState
Tracks cleaned files, selected file, chunks, next index.

### refreshChunkingFiles()
Calls /api/chunking/cleaned-files and renders file list.

### renderChunkingFileList()
Shows available cleaned files with chunk counts.

### selectChunkingFile(filename)
Sets selected source, displays source text, loads existing chunks, enables form.

### escapeHtml(text)
Prevents html injection in source display.

### loadChunksForFile(filename)
Calls /api/chunking/chunks/<filename>, updates next index and list.

### renderChunksList()
Renders existing chunk entries.

### enableChunkingForm() and disableChunkingForm()
Control form interactivity state.

### updateChunkCharCount()
Live count for chunk text field.

### clearChunkForm()
Clears chunk text and overlap fields.

### generateChunkId()
Client-side preview id generator.

### previewChunk()
Shows JSON preview modal before submit.

### handleChunkSubmit()
- Validates file and text
- POST /api/chunking/submit
- On success: clear form, set overlap hint, reload chunks, refresh lists and admin badge

### setupTextSelection()
Handles selecting source text to assist chunk drafting.

### initChunkingEventListeners()
Binds refresh, preview, submit, input, and helper events.

---

## 18) Services and their practical role

## 18.1 HuggingFaceService

File: app/services/huggingface.py

Methods:
- __init__: initializes token, API client, repo names
- is_configured: quick readiness check
- upload_raw_file: uploads txt + metadata json to raw repo
- upload_cleaned_file: uploads txt + metadata json to cleaned repo
- upload_chunk: uploads one chunk file under folder path
- upload_chunks: uploads many chunks
- list_raw_files: lists txt files from raw dataset repo
- download_file: downloads a file from selected stage repo
- sync_all_approved: batch local approved to HF

Runtime usage in current app:
- Directly used by admin push endpoint.

## 18.2 StorageService

File: app/services/storage.py

Methods:
- directory setup and path management
- get/list/save/approve/delete/stats helpers

Runtime usage in current app:
- Not currently used by route handlers (routes mostly do direct file I/O).
- It can be used in future refactor to reduce repeated logic.

---

## 19) Schemas model package

File: app/models/schemas.py

Data classes:
- RawDataSchema
- CleanedDataSchema
- ChunkSchema

Capabilities:
- type-structured constructors
- validation methods
- to_dict and metadata helper transforms
- chunk rag format helper

Runtime usage in current app:
- Mostly unused by route handlers right now.
- Current routes manually construct dictionaries.

This is a common intermediate state in growing projects: schema layer prepared, route code still imperative.

---

## 20) End-to-end call graphs (learning view)

### 20.1 Raw submission graph
1. User enters file/content in RAW tab
2. handleRawDataSubmit in raw-data.js
3. api wrapper in main.js
4. POST /api/raw/submit in raw_data.py
5. Validation + write pending files
6. JSON success response
7. Toast + form reset + admin badge refresh

### 20.2 Cleaning submission graph
1. User opens cleaning tab
2. refreshCleaningFiles calls /api/cleaning/raw-files
3. User selects file via selectCleaningFile
4. User submits via handleCleaningSubmit
5. POST /api/cleaning/submit in cleaning.py
6. Pending cleaned file written
7. UI refreshes statuses and admin counters

### 20.3 Chunk submission graph
1. User opens chunking tab and selects cleaned file
2. loadChunksForFile gets existing chunks
3. User creates chunk and submits
4. POST /api/chunking/submit in chunking.py
5. Next index computed; pending chunk json written
6. UI list and counts refreshed

### 20.4 Admin approval graph
1. Admin opens sidebar; refreshAdminData fetches /api/admin/pending
2. Admin approves or rejects
3. approve_submission or reject_submission in admin.py
4. File moves (approve) or deletes (reject)
5. Sidebar counts and lists refresh

### 20.5 HuggingFace sync graph
1. Admin enters HF token and repo in sidebar
2. pushToHuggingFace in main.js
3. POST /api/admin/push-to-hf
4. admin route loops approved data and calls HuggingFaceService uploads
5. Response includes per-stage success/failure counts
6. UI shows completion summary

---

## 21) Known implementation mismatches and caveats

1. Duplicate function definitions in static/js/main.js
- Last function wins at runtime.
- Can confuse maintenance and debugging.

2. Some route/service abstractions are prepared but not fully unified
- StorageService and schema classes are not the main execution path.

3. Auth model is minimal
- Admin routes are callable if endpoint is reachable.
- For public deployment, add real auth/authorization.

4. Local file storage limits horizontal scaling
- Multi-instance deployment needs shared persistent volume/object storage.

---

## 22) How to safely extend this project

Recommended extension order:
1. Add authentication to admin endpoints
2. Refactor route file I/O into StorageService
3. Replace manual dict validation with schema validate calls
4. Remove duplicate JS function definitions
5. Add audit log persistence beyond simple logger calls
6. Add API tests for route contracts

---

## 23) Learning exercises for you

1. Trace one request manually
- Put console.log in handleRawDataSubmit
- Put print/log in submit_raw_data
- Observe request and file outputs

2. Add a new source type end-to-end
- config source list
- UI select option
- submit and metadata verification

3. Add a new admin stat metric
- compute backend metric in get_stats
- display in sidebar

4. Refactor one route to StorageService
- Pick raw approve path first
- Compare behavior before/after

---

## 24) Quick reference map

Backend route files:
- app/routes/main.py
- app/routes/raw_data.py
- app/routes/cleaning.py
- app/routes/chunking.py
- app/routes/admin.py

Frontend behavior files:
- static/js/main.js
- static/js/raw-data.js
- static/js/cleaning.js
- static/js/chunking.js

Model/service files:
- app/models/schemas.py
- app/services/huggingface.py
- app/services/storage.py

UI shell:
- templates/index.html

---

## 25) Final summary

This project is a human-in-the-loop RAG data curation pipeline with:
- stage-based processing,
- moderation gates,
- local persistent workflow state,
- optional HuggingFace publication.

If you understand:
- the pending/approved directory transitions,
- the route called for each button click,
- and the admin moderation and push endpoints,
then you understand the core of the system.
