# SOW Task Generator — Design Spec
**Date:** 2026-03-16
**Status:** Approved

---

## Problem Statement

Customer Solution Consultants (CSCs) at Armakuni spend 1–2 hours per sprint manually creating tasks in Zoho Projects from SOW/WBS documents. This process is repetitive, error-prone, and takes time away from higher-value work. The goal is to automate task extraction and creation end-to-end.

---

## Solution Overview

A web app that:
1. Accepts a SOW/WBS document (via text paste or Google Docs URL)
2. Uses Claude AI to extract structured tasks
3. Presents tasks in an editable review table
4. Pushes approved tasks directly to a user-selected Zoho project via API

---

## Architecture

**Monorepo structure:**
```
sow-task-generator/
├── frontend/    # React + TypeScript + Vite + Tailwind CSS + shadcn/ui
└── backend/     # Python + FastAPI
```

**Stack:**
- Frontend: React + TypeScript + Vite + Tailwind CSS + shadcn/ui
- Backend: Python + FastAPI
- AI: Claude API (Anthropic) — model: `claude-sonnet-4-6`
- Integrations: Zoho Projects API, Google Docs API (public docs via API key)
- No user authentication (internal tool)
- Single Zoho portal (configured via `ZOHO_PORTAL_ID` env var)

---

## Task Data Model

The following schema is the canonical task structure used by both `/extract` (response) and `/push` (request). The only difference is that `/push` task objects must have `assignee_name` resolved — unresolved names are allowed (backend handles the fallback).

| Field | Type | Required | Notes |
|---|---|---|---|
| `task_name` | string | yes | Client-readable name |
| `description` | string | yes | What needs to be done |
| `assignee_name` | string | **no** | Display name; resolved to Zoho user ID on push; task created without assignee if unresolved |
| `estimated_hours` | number | yes | Decimal allowed (e.g. 1.5); min 0.5, max 999; validated on both frontend and backend |
| `billing_type` | enum | yes | `billable` or `non-billable`; defaults to `billable` if ambiguous in SOW |
| `sprint_milestone` | string | no | Free text; matched to existing Zoho milestones by name; silently dropped with warning if not found |
| `priority` | enum | no | `high`, `medium`, or `low` |
| `dependencies` | string[] | no | Task names; linked in second pass after all tasks created; unmatched names silently dropped with warning |
| `start_date` | date | no | ISO 8601 format: `YYYY-MM-DD`; validated on both frontend and backend |
| `end_date` | date | no | ISO 8601 format: `YYYY-MM-DD`; must be >= start_date if both set |

**Zoho field mappings:**
- `billing_type`: `billable` → `1`, `non-billable` → `2`
- `priority`: `high` → `1`, `medium` → `2`, `low` → `3`

---

## Zoho API Base URL Pattern

All Zoho Projects API calls use the following base URL pattern, with `ZOHO_PORTAL_ID` injected from the environment variable:

```
https://projectsapi.zoho.com/restapi/portal/{ZOHO_PORTAL_ID}/projects/{project_id}/...
```

Example: creating a task → `POST https://projectsapi.zoho.com/restapi/portal/{ZOHO_PORTAL_ID}/projects/{project_id}/tasks/`

---

## Backend Endpoints

### `GET /zoho/projects`
Fetches active Zoho projects in the configured portal via `GET /portal/{portal_id}/projects/?status=active`.
- Response:
  ```json
  { "projects": [{ "id": "string", "name": "string" }] }
  ```

### `GET /zoho/projects/{project_id}/members`
Fetches project-level users via Zoho's `GET /portal/{portal_id}/projects/{project_id}/users/` endpoint. The same population is used for both the assignee dropdown in the frontend and assignee name resolution in `/push`.
- Response:
  ```json
  { "members": [{ "id": "string", "name": "string" }] }
  ```

### `GET /zoho/projects/{project_id}/milestones`
Fetches existing milestones for the selected project via `GET /portal/{portal_id}/projects/{project_id}/milestones/`. Used by the frontend for milestone autocomplete in the task table, and by `/push` for name-based milestone resolution.
- Response:
  ```json
  { "milestones": [{ "id": "string", "name": "string" }] }
  ```

### `GET /google-doc?url={encoded_url}`
Fetches plain text from a publicly shared Google Doc using the **Google Drive export API**: `GET https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain&key={GOOGLE_API_KEY}`. This endpoint handles all formatting, tables, and structure natively — no custom parsing required.
- Query param: `url` — URL-encoded Google Doc URL; backend extracts the doc ID from the URL
- Response: `{ "text": "string" }`
- Error responses: `400` if URL is invalid or doc ID cannot be extracted; `403` if doc is not publicly accessible

### `POST /extract`
Calls Claude API to extract structured tasks from SOW text. Input is capped at **50,000 characters**.
- Request body:
  ```json
  {
    "sow_text": "string (max 50,000 chars)",
    "team_members": ["string"]
  }
  ```
- Response:
  ```json
  { "tasks": [ ...array of task objects matching the Task Data Model schema... ] }
  ```
- Claude prompt outline:
  - System: instruct Claude to act as a project task extractor; return only valid JSON matching the Task Data Model schema exactly; no prose
  - User: inject `sow_text` and `team_members` list; instruct Claude to suggest assignee names only from the provided list; default `billing_type` to `"billable"` when ambiguous; set `estimated_hours` to `1.0` if not determinable from the SOW (never null); set all other optional fields to `null` if not determinable
- `estimated_hours` will always be a number in Claude's output (defaulting to `1.0`); the frontend highlights these default values in amber so the user can review before pushing
- If Claude response cannot be parsed as valid JSON matching the schema: return `422` with `{ "error": "parse_failed", "raw_response": "string" }`

### `POST /push`
Creates all tasks in the selected Zoho project. **Best-effort, not transactional** — each task is processed independently; a failure on one does not block others.

Two-pass execution:
1. Create all tasks; collect `zoho_task_id` per task
2. For tasks with `dependencies`: match dependency names to `zoho_task_id`s created in pass one; link via Zoho dependency API; if a dependency's source task failed in pass one, add a warning "dependency '{name}' could not be linked: source task failed to create"

- Request body:
  ```json
  {
    "project_id": "string",
    "tasks": [
      {
        "row_id": "string (client-side UUID, echoed back in results)",
        ...task fields per Task Data Model...
      }
    ]
  }
  ```
- Backend validates: `estimated_hours` (0.5–999), `start_date`/`end_date` format and ordering, `billing_type` and `priority` enum values. Returns `400` with field-level errors if validation fails.
- Assignee resolution: `assignee_name` matched case-insensitively against project members fetched from the same `/zoho/projects/{id}/members` endpoint. Unmatched → task created without assignee + warning.
- `sprint_milestone`: matched case-insensitively against milestones fetched lazily during push. Not found → field dropped + warning.
- Milestones are fetched once per `/push` call (not cached between calls).
- Response: always `HTTP 200` for task-level operations. `503` for total Zoho API outage. `400` for invalid `project_id` or validation failure.
  ```json
  {
    "results": [
      {
        "row_id": "string (echoed from request)",
        "task_name": "string",
        "status": "created | failed | warning",
        "zoho_task_id": "string | null",
        "warnings": ["string"],
        "error": "string | null"
      }
    ]
  }
  ```

---

## User Flow

1. User opens the app
2. Selects a Zoho project from a dropdown (fetched on page load)
3. Team members auto-fetched from the selected project
4. Chooses input method: paste SOW text OR enter Google Doc URL
5. Clicks "Extract Tasks" → backend calls Claude, returns structured task list
6. Reviews tasks in editable table — can edit any field, add or delete rows
7. Clicks "Push to Zoho" → tasks created in selected project
8. Per-task results shown in FeedbackPanel (created / warning / failed)

---

## Frontend Components

- **ProjectSelector** — dropdown populated on page load from `/zoho/projects`; triggers `/zoho/projects/{id}/members` on selection
- **InputPanel** — toggle between text paste and Google Doc URL input
- **ExtractButton** — calls `/extract`; disabled if no SOW input or no project selected; shows loading spinner; disabled if SOW text exceeds 50,000 characters (character counter shown)
- **TaskTable** — editable table; each row has a client-side UUID (`row_id`) for identity (included in push request, echoed in results for deterministic row-to-result mapping); inline edit on all fields; add row, delete row; required fields highlighted red if empty; `estimated_hours` defaulted to `1.0` by Claude highlighted in amber; assignee field rendered as dropdown from fetched members; sprint_milestone rendered as autocomplete from `/zoho/projects/{id}/milestones`
- **PushButton** — calls `/push`; disabled if no tasks, or any required field is empty, or `estimated_hours` is out of range, or `end_date` < `start_date`
- **FeedbackPanel** — shows per-task results with status badge (created / warning / failed) and warning/error messages

**Validation (frontend):**
- Required fields (`task_name`, `description`, `estimated_hours`, `billing_type`) must be non-empty before push
- `estimated_hours`: positive decimal, min 0.5, max 999
- `end_date` >= `start_date` if both set
- Push button disabled if any required field is empty; red cell highlight on offending fields

---

## Error Handling

| Scenario | Backend | Frontend |
|---|---|---|
| Google Doc not public or invalid URL | 400 / 403 | Inline error below URL input |
| Claude parse failure | 422 with raw output | Error message + allow manual task entry |
| SOW text over 50,000 chars | 400 | Character counter turns red; Extract button disabled |
| Zoho API unreachable | 503 | Banner with retry button |
| Invalid project_id or body validation | 400 with field errors | Display field-level error messages |
| Assignee not found in Zoho | 200, status=warning | Warning in FeedbackPanel per task |
| sprint_milestone not found in Zoho | 200, status=warning | Warning in FeedbackPanel per task |
| Dependency name mismatch | 200, status=warning | Warning in FeedbackPanel per task |
| Partial task push failure | 200, per-task status | FeedbackPanel shows each task's status |
| API timeout | — | 60s for `/extract`, 30s for others; manual retry button shown (user must check Zoho for duplicates before retrying `/push`) |

---

## Zoho Authentication

OAuth 2.0 self-client flow (server-to-server). Required OAuth scopes:
- `ZohoProjects.portals.READ`
- `ZohoProjects.projects.READ`
- `ZohoProjects.tasks.CREATE`
- `ZohoProjects.tasks.UPDATE` (for dependency linking)
- `ZohoProjects.milestones.READ`
- `ZohoProjects.users.READ`

**Refresh token rotation:** Zoho rotates refresh tokens on each use. The new refresh token returned after each access token refresh is written back to a local `zoho_token.json` file in the backend directory. The `zoho_client` reads from this file on startup (falling back to `ZOHO_REFRESH_TOKEN` env var if the file doesn't exist) and overwrites it after every token refresh. If the stored token is expired on startup, the backend logs a clear error and refuses to start, instructing the operator to re-generate a refresh token via the Zoho self-client console.

`zoho_client` handles token refresh automatically before each API call using `ZOHO_CLIENT_ID` and `ZOHO_CLIENT_SECRET` from env.

---

## Environment Variables

```env
# Backend (.env)
ANTHROPIC_API_KEY=
ZOHO_CLIENT_ID=
ZOHO_CLIENT_SECRET=
ZOHO_REFRESH_TOKEN=
ZOHO_PORTAL_ID=
GOOGLE_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:5173  # comma-separated for production

# Frontend (.env)
VITE_API_BASE_URL=http://localhost:8000
```

---

## Development Setup

- Frontend: `http://localhost:5173` (Vite default)
- Backend: `http://localhost:8000` (FastAPI default)
- FastAPI CORS configured via `CORS_ALLOWED_ORIGINS` env var

---

## Key Decisions

- API keys server-side only; never exposed to browser
- Public Google Docs only (API key); private docs not supported in v1
- Single Zoho portal per deployment
- Team members fetched from selected Zoho project; assignee dropdown in task table
- `assignee_name` is optional — unresolved names create tasks without assignee + warning
- `sprint_milestone` matched by name; not found → silently dropped with warning
- Dependencies: two-pass creation; unmatched names silently dropped with warning
- `billing_type` defaults to `billable` when ambiguous
- SOW input capped at 50,000 characters
- Claude model: `claude-sonnet-4-6`
- `/push` retry is manual; user must check Zoho for duplicates before retrying

---

## Out of Scope (v1)

- User authentication
- Private Google Docs access
- Saved project templates
- Task history / audit log
- Bulk SOW processing
- Multi-portal Zoho support
- Jira or other PM tool integrations
- Automatic duplicate detection on push retry
