# Multi-Assignee Selection — Design Spec

**Date:** 2026-03-25
**Status:** Approved

## Overview

Change the assignee field from a single-value select to a multi-select dropdown across the task table, bulk edit toolbar, and Zoho push logic.

## Data Model

### Frontend (`frontend/src/types/task.ts`)
- Remove `assignee_name: string | null`
- Add `assignee_names: string[]` (empty array = unassigned)

### Backend (`backend/models/task.py`)
- Remove `assignee_name: str | None`
- Add `assignee_names: list[str]` (default `[]`)

### Validation (`frontend/src/utils/validation.ts`)
- `assignee` field is valid when `assignee_names.length > 0`

## UI Component: `AssigneeMultiSelect`

A custom dropdown component defined inside `TaskTable.tsx` (no separate file).

**Closed state:**
- Renders as a styled `<div>` matching existing `cellClass` borders and sizing
- Displays `— unassigned —` when `assignee_names` is empty
- Displays comma-separated names when one or more are selected (e.g., `Alice, Bob`)

**Open state:**
- Absolutely-positioned checklist panel below the trigger
- One row per project member: checkbox + full name
- Click outside (or press Escape) to close
- Uses `useRef` + `useEffect` for click-outside detection

**Props:**
```ts
interface AssigneeMultiSelectProps {
  value: string[]
  members: ZohoMember[]
  onChange: (names: string[]) => void
  hasError?: boolean
}
```

## Bulk Edit Toolbar

- `bulkAssignee: string` state becomes `bulkAssignees: string[]`
- The existing `<select>` for assignee is replaced with `AssigneeMultiSelect`
- On apply (when `bulkAssignees.length > 0`): **merge** selected assignees into each selected row's existing `assignee_names` using set union — existing assignees are never removed
- After apply, reset `bulkAssignees` to `[]`

## Zoho Push (`backend/routers/push_router.py`)

- Rename `_resolve_assignee` → `_resolve_assignees`
- New signature: `_resolve_assignees(assignee_names: list[str], members: list[dict]) -> tuple[str | None, list[str]]`
  - Returns `(comma_separated_ids, warnings)`
  - Iterates over each name, resolves to Zoho user ID
  - Warns for each unresolved name: `"Assignee 'X' not found in project members"`
  - Joins resolved IDs with `,` (e.g., `"123,456"`)
- `_build_task_payload` passes `person_responsible` as the comma-separated ID string

## CSV Export (`frontend/src/components/TaskTable.tsx`)

- Rename column `assignee_name` → `assignee_names` in `CSV_COLUMNS`
- Render value as semicolon-separated string (e.g., `Alice;Bob`) to avoid conflicts with the comma delimiter

## Affected Files

| File | Change |
|------|--------|
| `frontend/src/types/task.ts` | Replace `assignee_name` with `assignee_names` |
| `frontend/src/utils/validation.ts` | Update assignee validation rule |
| `frontend/src/components/TaskTable.tsx` | Add `AssigneeMultiSelect`, update bulk toolbar, update CSV |
| `backend/models/task.py` | Replace `assignee_name` with `assignee_names` |
| `backend/routers/push_router.py` | Update resolver and payload builder |

## Out of Scope

- No changes to the extract/Claude prompt (AI still outputs a single assignee name string; backend or frontend can coerce to array on receipt)
- No changes to the Google Docs or InputPanel flows
