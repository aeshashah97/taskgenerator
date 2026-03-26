# SOW Task Generator

## Project Overview
A web app that reads a Statement of Work (SOW) / WBS document, uses AI to extract structured tasks, lets the user review and edit them, then pushes them directly to Zoho Projects via API.

## Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + shadcn/ui
- **Backend**: Python + FastAPI
- **AI**: Claude API (Anthropic)
- **Integrations**: Zoho Projects API, Google Docs API

## Architecture
- Monorepo with `frontend/` and `backend/` directories
- No authentication (internal tool)
- Three backend endpoints:
  - `POST /extract` — accepts SOW text, calls Claude, returns structured task list
  - `GET /google-doc` — accepts Google Doc URL, fetches and returns plain text
  - `POST /push` — accepts reviewed task list, creates tasks in Zoho Projects

## Task Data Model
| Field | Required |
|---|---|
| task_name | yes |
| description | yes |
| assignee | yes |
| estimated_hours | yes |
| billing_type (billable / non-billable) | yes |
| priority (high / medium / low) | no |
| dependencies | no |
| start_date | no |
| end_date | no |

## Key Decisions
- API keys are kept server-side (backend) for security
- v1 supports both text paste and Google Docs URL as SOW input
- Direct Zoho API push (no CSV export step)
