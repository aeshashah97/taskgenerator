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
- Add a Pydantic `@field_validator('assignee_names', mode='before')` that accepts `str | None | list[str]`:
  - `None` → `[]`
  - `""` → `[]`
  - `"Alice"` → `["Alice"]`
  - `["Alice", "Bob"]` → `["Alice", "Bob"]`
  - This ensures Claude's current single-string output (or `null`) is normalised at the API boundary without any frontend changes.

### Validation (`frontend/src/utils/validation.ts`)
- `assignee` field is valid when `assignee_names.length > 0`

## UI Component: `AssigneeMultiSelect`

A custom dropdown component defined inside `TaskTable.tsx` (no separate file needed — it is ~60 lines).

**Closed state:**
- Renders as a styled `<div>` matching existing `cellClass` borders and sizing
- When `hasError` is `true`: applies `border-red-500 bg-red-50` (same as all other error cells via `cellClass`)
- Displays `— unassigned —` when `assignee_names` is empty
- Displays comma-separated names when one or more are selected (e.g., `Alice, Bob`)

**Open state:**
- Absolutely-positioned checklist panel below the trigger
- One row per project member: checkbox + full name
- Click outside (via `useRef` + `useEffect` on `mousedown`) closes the panel
- Keyboard accessibility (arrow keys, Enter/Space) is **out of scope** for this version

**Props:**
```ts
interface AssigneeMultiSelectProps {
  value: string[]
  members: ZohoMember[]
  onChange: (names: string[]) => void
  hasError?: boolean
}
```

## Task Table (`frontend/src/components/TaskTable.tsx`)

### `emptyTask()` factory
- Change `assignee_name: null` → `assignee_names: []`
- Remove the stale `sprint_milestone: null` field (does not exist on the `Task` interface)

### Per-row assignee cell
- Replace the `<select>` with `<AssigneeMultiSelect>` passing `value={task.assignee_names}`, `members`, `onChange`, and `hasError`

### Bulk edit toolbar
- `bulkAssignee: string` state → `bulkAssignees: string[]`
- Replace the assignee `<select>` with `<AssigneeMultiSelect value={bulkAssignees} ... />`
- On apply (when `bulkAssignees.length > 0`): **merge** into each selected row using set union.
  - This cannot reuse the generic `bulkUpdate` helper (which does a simple spread/replace). Implement a dedicated `applyBulkAssignees` function:
    ```ts
    function applyBulkAssignees() {
      if (bulkAssignees.length === 0) return
      onChange(tasks.map(t =>
        selectedIds.has(t.row_id)
          ? { ...t, assignee_names: [...new Set([...t.assignee_names, ...bulkAssignees])] }
          : t
      ))
      setBulkAssignees([])
    }
    ```

### CSV export
- Rename `'assignee_name'` → `'assignee_names'` in `CSV_COLUMNS`
- The generic `csvField` function calls `String(value)` which would produce `"Alice,Bob"` for an array (comma triggers quoting). Instead, add a dedicated serialiser for array fields:
  ```ts
  function csvField(col: keyof Task, value: unknown): string {
    if (col === 'assignee_names') {
      return csvEscape((value as string[]).join(';'))
    }
    // existing logic...
  }
  ```
  Assignees are joined with `;` (semicolon) to avoid conflict with the CSV comma delimiter.

## Zoho Push (`backend/routers/push_router.py`)

### Rename and update `_resolve_assignee` → `_resolve_assignees`
```python
def _resolve_assignees(
    assignee_names: list[str], members: list[dict]
) -> tuple[str | None, list[str]]:
    """Returns (comma_separated_ids_or_None, warnings)."""
    if not assignee_names:
        return None, []
    resolved_ids = []
    warnings = []
    for name in assignee_names:
        for m in members:
            if m["name"].lower() == name.lower():
                resolved_ids.append(m["id"])
                break
        else:
            warnings.append(
                f"Assignee '{name}' not found in project members — skipped"
            )
    return (",".join(resolved_ids) if resolved_ids else None), warnings
```

### Update `_build_task_payload`
New signature: `_build_task_payload(task, assignee_ids: str | None) -> dict`
- `person_responsible` is set to `assignee_ids` (the comma-separated ID string) when non-None

### Update call site in `push_tasks`
```python
assignee_ids, aws = _resolve_assignees(task.assignee_names, members)
warnings.extend(aws)
payload = _build_task_payload(task, assignee_ids)
```

## Backend Tests

All three test files use the old `assignee_name` field in fixtures and must be updated:

| File | Change |
|------|--------|
| `backend/tests/test_task_models.py` | Replace `assignee_name` with `assignee_names` in all fixtures; add validator tests for `str → list`, `None → []` coercion |
| `backend/tests/test_push_router.py` | Replace `assignee_name` in `make_push_task()`; rename `_resolve_assignee` import → `_resolve_assignees`; rewrite `TestResolveAssignee` test cases for new signature |
| `backend/tests/test_extract_router.py` | Replace `assignee_name` in `VALID_TASK` fixture |

### New test cases required for `_resolve_assignees`

| Scenario | Expected |
|----------|----------|
| Empty list | `(None, [])` |
| Two names both resolved | `("id1,id2", [])` |
| One resolved, one not | `("id1", ["Assignee 'X' not found..."])` |
| All names unresolved | `(None, [warning per name])` |

## Affected Files

| File | Change |
|------|--------|
| `frontend/src/types/task.ts` | Replace `assignee_name` with `assignee_names` |
| `frontend/src/utils/validation.ts` | Update assignee validation rule |
| `frontend/src/components/TaskTable.tsx` | Add `AssigneeMultiSelect`, update `emptyTask`, update bulk toolbar, update CSV serialiser |
| `frontend/src/api/client.ts` | Review after type change (no logic change expected; TypeScript will surface any mismatches) |
| `backend/models/task.py` | Replace `assignee_name` with `assignee_names`; add field validator |
| `backend/routers/push_router.py` | Update resolver and payload builder |
| `backend/tests/test_push_router.py` | Update fixtures and test cases |
| `backend/tests/test_task_models.py` | Update fixtures; add validator tests |
| `backend/tests/test_extract_router.py` | Update `VALID_TASK` fixture |

## Out of Scope

- Changes to the Claude prompt (AI may return `null` or a single name; the backend validator normalises either to `[]` or `["name"]`)
- Changes to the Google Docs or InputPanel flows
- Keyboard accessibility for `AssigneeMultiSelect` (arrow keys, Enter/Space)
