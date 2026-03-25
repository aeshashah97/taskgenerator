# Multi-Assignee Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-assignee field with a multi-select dropdown across the task table, bulk toolbar, and Zoho push — storing `assignee_names: string[]` instead of `assignee_name: string | null`.

**Architecture:** Data model change flows from backend Pydantic model → frontend TypeScript type → UI component. A Pydantic field validator normalises Claude's single-string output at the API boundary so no prompt changes are needed. A custom `AssigneeMultiSelect` component inside `TaskTable.tsx` handles per-row and bulk-edit selection. The Zoho push resolver is updated to join multiple user IDs with a comma for the `person_responsible` field.

**Tech Stack:** React + TypeScript (frontend), Python + FastAPI + Pydantic v2 (backend), pytest (backend tests)

---

## Task 1: Update backend data model

**Files:**
- Modify: `backend/models/task.py`
- Modify: `backend/tests/test_task_models.py`

- [ ] **Step 1: Write failing tests for the new `assignee_names` field**

Open `backend/tests/test_task_models.py`. Replace the two references to `assignee_name` and add validator tests. The full updated `TestTask` class:

```python
class TestTask:
    def test_minimal_valid_task(self):
        task = Task(
            task_name="Set up repo",
            description="Initialize the project repository",
            estimated_hours=2.0,
            billing_type="billable",
        )
        assert task.task_name == "Set up repo"
        assert task.assignee_names == []   # changed from assignee_name is None
        assert task.priority is None
        assert task.dependencies == []
        assert task.start_date is None
        assert task.end_date is None

    def test_full_valid_task(self):
        task = Task(
            task_name="Build API",
            description="Implement REST endpoints",
            assignee_names=["Alice"],       # changed from assignee_name="Alice"
            estimated_hours=8.0,
            billing_type="non-billable",
            priority="high",
            dependencies=["Set up repo"],
            start_date="2026-03-17",
            end_date="2026-03-20",
        )
        assert task.billing_type == "non-billable"
        assert task.priority == "high"

    # --- Add these new validator tests ---

    def test_assignee_names_accepts_list(self):
        task = Task(
            task_name="X", description="Y", estimated_hours=1.0,
            billing_type="billable", assignee_names=["Alice", "Bob"],
        )
        assert task.assignee_names == ["Alice", "Bob"]

    def test_assignee_names_coerces_single_string(self):
        task = Task(
            task_name="X", description="Y", estimated_hours=1.0,
            billing_type="billable", assignee_names="Alice",
        )
        assert task.assignee_names == ["Alice"]

    def test_assignee_names_coerces_none_to_empty(self):
        task = Task(
            task_name="X", description="Y", estimated_hours=1.0,
            billing_type="billable", assignee_names=None,
        )
        assert task.assignee_names == []

    def test_assignee_names_coerces_empty_string_to_empty(self):
        task = Task(
            task_name="X", description="Y", estimated_hours=1.0,
            billing_type="billable", assignee_names="",
        )
        assert task.assignee_names == []

    def test_assignee_names_defaults_to_empty(self):
        task = Task(
            task_name="X", description="Y", estimated_hours=1.0,
            billing_type="billable",
        )
        assert task.assignee_names == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/Scripts/activate && pytest tests/test_task_models.py -v
```

Expected: multiple FAILs — `assignee_name` attribute not found / `assignee_names` not defined.

- [ ] **Step 3: Update `backend/models/task.py`**

Replace `assignee_name: Optional[str] = None` with the new field and validator. Also add `field_validator` to the imports:

```python
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


BillingType = Literal["billable", "non-billable"]
Priority = Literal["high", "medium", "low"]
TaskStatus = Literal["created", "failed", "warning"]


class Task(BaseModel):
    task_name: str
    description: str
    assignee_names: list[str] = Field(default_factory=list)
    estimated_hours: Optional[float] = Field(None, ge=0.5, le=999)
    billing_type: BillingType
    priority: Optional[Priority] = None
    dependencies: list[str] = Field(default_factory=list)
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD

    @field_validator('assignee_names', mode='before')
    @classmethod
    def coerce_assignee_names(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [v]
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> Task:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be >= start_date")
        return self
```

Keep `PushTask`, `ExtractRequest`, `ExtractResponse`, `PushRequest`, `PushTaskResult`, `PushResponse` unchanged.

- [ ] **Step 4: Run task model tests only**

```bash
pytest tests/test_task_models.py -v
```

Expected: all PASS. **Do not run `pytest tests/` here** — `test_push_router.py` still uses the old `assignee_name` field (it will be updated in Task 2) and running all tests now would produce a misleading premature failure.

- [ ] **Step 5: Commit**

```bash
git add backend/models/task.py backend/tests/test_task_models.py
git commit -m "feat: replace assignee_name with assignee_names list in Task model"
```

---

## Task 2: Update backend push router

**Files:**
- Modify: `backend/routers/push_router.py`
- Modify: `backend/tests/test_push_router.py`

- [ ] **Step 1: Write failing tests for `_resolve_assignees`**

In `backend/tests/test_push_router.py`:

1. Change the import on line 5:
   ```python
   from routers.push_router import _resolve_assignees
   ```

2. Replace the entire `TestResolveAssignee` class with:
   ```python
   class TestResolveAssignees:
       MEMBERS = [{"id": "u1", "name": "Alice"}, {"id": "u2", "name": "Bob"}]

       def test_empty_list_returns_none_no_warnings(self):
           ids, warnings = _resolve_assignees([], self.MEMBERS)
           assert ids is None
           assert warnings == []

       def test_two_names_both_resolved(self):
           ids, warnings = _resolve_assignees(["Alice", "Bob"], self.MEMBERS)
           assert ids == "u1,u2"
           assert warnings == []

       def test_case_insensitive_match(self):
           ids, warnings = _resolve_assignees(["alice"], self.MEMBERS)
           assert ids == "u1"
           assert warnings == []

       def test_one_resolved_one_not(self):
           ids, warnings = _resolve_assignees(["Alice", "Unknown"], self.MEMBERS)
           assert ids == "u1"
           assert len(warnings) == 1
           assert "Unknown" in warnings[0]

       def test_all_unresolved_returns_none_with_warnings(self):
           ids, warnings = _resolve_assignees(["Ghost"], self.MEMBERS)
           assert ids is None
           assert len(warnings) == 1
           assert "Ghost" in warnings[0]
   ```

3. Update `make_push_task` — change `"assignee_name": "Alice"` to `"assignee_names": ["Alice"]`:
   ```python
   def make_push_task(overrides=None):
       task = {
           "row_id": "row-1",
           "task_name": "Set up repo",
           "description": "Init project",
           "assignee_names": ["Alice"],
           "estimated_hours": 2.0,
           "billing_type": "billable",
           "priority": None,
           "dependencies": [],
           "start_date": None,
           "end_date": None,
       }
       if overrides:
           task.update(overrides)
       return task
   ```

4. Update `test_push_warns_when_assignee_not_found` — change `{"assignee_name": "Unknown Person"}` to `{"assignee_names": ["Unknown Person"]}`:
   ```python
   def test_push_warns_when_assignee_not_found(zoho_mock):
       test_client, _ = zoho_mock
       task = make_push_task({"assignee_names": ["Unknown Person"]})
       ...
   ```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_push_router.py -v
```

Expected: the **entire module fails to import** with `ImportError: cannot import name '_resolve_assignees' from 'routers.push_router'` — this is the expected red state. No individual tests will run; the whole file errors. The `make_push_task` body change (item 3 above) is sufficient to fix all downstream integration tests once the router is updated — no other test functions need editing.

- [ ] **Step 3: Update `backend/routers/push_router.py`**

Replace `_resolve_assignee` and update `_build_task_payload` and the call site:

```python
import httpx
from fastapi import APIRouter, HTTPException
from clients.zoho_client import ZohoClient
from models.task import PushRequest, PushResponse, PushTaskResult

router = APIRouter()

PRIORITY_MAP = {"high": "High", "medium": "Medium", "low": "Low"}


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


def _zoho_date(iso_date: str | None) -> str | None:
    """Convert YYYY-MM-DD to MM-DD-YYYY for Zoho."""
    if not iso_date:
        return None
    try:
        y, m, d = iso_date.split("-")
        return f"{m}-{d}-{y}"
    except Exception:
        return None


def _build_task_payload(task, assignee_ids: str | None) -> dict:
    payload = {
        "name": task.task_name,
        "description": task.description,
    }
    if task.estimated_hours:
        payload["duration"] = str(round(task.estimated_hours / 8, 2))
    if assignee_ids:
        payload["person_responsible"] = assignee_ids
    if task.priority:
        payload["priority"] = PRIORITY_MAP[task.priority]
    start = _zoho_date(task.start_date)
    if start:
        payload["start_date"] = start
    end = _zoho_date(task.end_date)
    if end:
        payload["end_date"] = end
    return payload


@router.post("/push", response_model=PushResponse)
def push_tasks(request: PushRequest):
    try:
        zoho = ZohoClient()
        members = zoho.get_members(request.project_id)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")

    results: list[PushTaskResult] = []
    name_to_zoho_id: dict[str, str] = {}
    failed_task_names: set[str] = set()

    # Pass 1: create all tasks independently
    for task in request.tasks:
        warnings = []
        assignee_ids, aws = _resolve_assignees(task.assignee_names, members)
        warnings.extend(aws)
        try:
            payload = _build_task_payload(task, assignee_ids)
            zoho_task = zoho.create_task(request.project_id, payload)
            zoho_id = zoho_task.get("id_string") or zoho_task.get("id")
            name_to_zoho_id[task.task_name] = zoho_id
            status = "warning" if warnings else "created"
            results.append(PushTaskResult(
                row_id=task.row_id,
                task_name=task.task_name,
                status=status,
                zoho_task_id=zoho_id,
                warnings=warnings,
            ))
        except Exception as e:
            failed_task_names.add(task.task_name)
            results.append(PushTaskResult(
                row_id=task.row_id,
                task_name=task.task_name,
                status="failed",
                warnings=warnings,
                error=str(e),
            ))

    # Pass 2: link dependencies
    for task in request.tasks:
        if not task.dependencies:
            continue
        result = next((r for r in results if r.row_id == task.row_id), None)
        if not result or result.status == "failed":
            continue
        task_zoho_id = result.zoho_task_id
        for dep_name in task.dependencies:
            dep_zoho_id = name_to_zoho_id.get(dep_name)
            if not dep_zoho_id:
                if dep_name in failed_task_names:
                    result.warnings.append(
                        f"dependency '{dep_name}' could not be linked: source task failed to create"
                    )
                else:
                    result.warnings.append(
                        f"dependency '{dep_name}' could not be linked: source task not found"
                    )
                if result.status == "created":
                    result.status = "warning"
                continue
            try:
                zoho.add_dependency(request.project_id, task_zoho_id, dep_zoho_id)
            except Exception as e:
                result.warnings.append(f"Failed to link dependency '{dep_name}': {e}")
                if result.status == "created":
                    result.status = "warning"

    return PushResponse(results=results)
```

- [ ] **Step 4: Run all backend tests**

```bash
pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/push_router.py backend/tests/test_push_router.py
git commit -m "feat: update push router for multi-assignee support"
```

---

## Task 3: Update extract router test fixture

**Files:**
- Modify: `backend/tests/test_extract_router.py`

- [ ] **Step 1: Update `VALID_TASK` fixture**

In `backend/tests/test_extract_router.py`, change line 9:
```python
# Before:
"assignee_name": "Alice",

# After:
"assignee_names": ["Alice"],
```

- [ ] **Step 2: Run extract tests**

```bash
pytest tests/test_extract_router.py -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_extract_router.py
git commit -m "test: update extract router fixture for assignee_names"
```

---

## Task 4: Update frontend TypeScript type

**Files:**
- Modify: `frontend/src/types/task.ts`

- [ ] **Step 1: Update `Task` interface**

In `frontend/src/types/task.ts`, replace line 13:
```ts
// Before:
assignee_name: string | null

// After:
assignee_names: string[]
```

The `ExtractRequest` and `PushRequest` interfaces are unchanged. TypeScript will now surface every usage of `assignee_name` as a compile error — those are fixed in the next tasks.

- [ ] **Step 2: Verify TypeScript errors surface**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -40
```

Expected: errors in `validation.ts`, `TaskTable.tsx`, `api/client.ts` referencing `assignee_name`. This confirms all affected locations are identified.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/task.ts
git commit -m "feat: change Task.assignee_name to assignee_names string[]"
```

---

## Task 5: Update frontend validation

**Files:**
- Modify: `frontend/src/utils/validation.ts`

- [ ] **Step 1: Add assignee validation**

In `frontend/src/utils/validation.ts`, add an assignee check inside `validateTasksForPush`. The full updated function:

```ts
export function validateTasksForPush(tasks: Task[]): ValidationError[] {
  return tasks.flatMap((task) => {
    const fields: string[] = []
    if (!task.task_name.trim()) fields.push('task_name')
    if (!task.description.trim()) fields.push('description')
    if (task.assignee_names.length === 0) fields.push('assignee_names')
    const hours = task.estimated_hours
    if (hours !== null && hours !== undefined && (isNaN(hours) || hours < 0.5 || hours > 999)) fields.push('estimated_hours')
    if (!task.billing_type) fields.push('billing_type')
    if (task.start_date && task.end_date && task.end_date < task.start_date) {
      fields.push('end_date')
    }
    return fields.length > 0 ? [{ row_id: task.row_id, fields }] : []
  })
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
npx tsc --noEmit 2>&1 | grep validation
```

Expected: no errors in `validation.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/validation.ts
git commit -m "feat: add assignee_names required validation"
```

---

## Task 6: Update TaskTable — data wiring and CSV

**Files:**
- Modify: `frontend/src/components/TaskTable.tsx`

This task wires up the data model changes without yet adding the `AssigneeMultiSelect` component. Goal: get the file to compile cleanly.

- [ ] **Step 1: Fix `emptyTask`, `CSV_COLUMNS`, `csvField`, and bulk state**

Make these targeted changes to `TaskTable.tsx`:

**a) `emptyTask()` factory** — remove `sprint_milestone`, change `assignee_name`:
```ts
function emptyTask(): Task {
  return {
    row_id: uuidv4(),
    task_name: '',
    description: '',
    assignee_names: [],          // was: assignee_name: null
    estimated_hours: null,
    billing_type: 'billable',
    priority: null,
    dependencies: [],
    start_date: null,
    end_date: null,
  }
}
```

**b) Bulk state** — at the top of the `TaskTable` component body, change:
```ts
// Before:
const [bulkAssignee, setBulkAssignee] = useState('')

// After:
const [bulkAssignees, setBulkAssignees] = useState<string[]>([])
```

**Apply sub-items c and d together in a single edit pass** — updating `csvField`'s signature (c) before updating `buildCsv`'s call site (d) will produce a TypeScript error mid-step. Make both changes before running `tsc`.

**c) `csvField` function** — update signature and add array branch:
```ts
function csvField(col: keyof Task, value: unknown): string {
  if (col === 'assignee_names') {
    const names = (value as string[])
    const joined = names.join(';')
    if (joined.includes('"') || joined.includes('\n')) {
      return '"' + joined.replace(/"/g, '""') + '"'
    }
    return joined
  }
  if (value === null || value === undefined) return ''
  const str = String(value)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}
```

**d) `buildCsv`** — update the map call to pass the column key:
```ts
function buildCsv(tasks: Task[]): string {
  const header = CSV_COLUMNS.join(',')
  const rows = tasks.map(t => CSV_COLUMNS.map(col => csvField(col, t[col])).join(','))
  return [header, ...rows].join('\r\n')
}
```

**e) `CSV_COLUMNS`** — rename the column:
```ts
const CSV_COLUMNS: (keyof Task)[] = [
  'task_name', 'description', 'assignee_names', 'estimated_hours',
  'billing_type', 'priority', 'start_date', 'end_date',
]
```

- [ ] **Step 2: Temporarily stub the assignee cell and bulk assignee control**

For the per-row assignee cell (around line 226), replace the `<select>` with a plain `<div>` stub so the file compiles:
```tsx
<td className="p-1 border border-slate-200">
  <div className={cellClass(task.row_id, 'assignee_names')}>
    {task.assignee_names.length > 0 ? task.assignee_names.join(', ') : '— unassigned —'}
  </div>
</td>
```

For the bulk assignee `<select>` in the toolbar, replace with a stub `<span>` for now:
```tsx
{/* AssigneeMultiSelect bulk — coming in Task 7 */}
<span className="text-xs text-slate-400">assignee multi-select (todo)</span>
```

Also add a stub `applyBulkAssignees` function (no-op for now):
```ts
function applyBulkAssignees() { /* implemented in Task 7 */ }
```

- [ ] **Step 3: Verify TypeScript compiles cleanly**

```bash
npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TaskTable.tsx
git commit -m "feat: wire assignee_names into TaskTable (stub UI)"
```

---

## Task 7: Implement `AssigneeMultiSelect` component

**Files:**
- Modify: `frontend/src/components/TaskTable.tsx`

- [ ] **Step 1: Add the `AssigneeMultiSelect` component**

Add this component definition near the top of `TaskTable.tsx`, just before `TaskTable` function — after the helper functions (`csvField`, `buildCsv`, etc.):

```tsx
interface AssigneeMultiSelectProps {
  value: string[]
  members: ZohoMember[]
  onChange: (names: string[]) => void
  hasError?: boolean
}

function AssigneeMultiSelect({ value, members, onChange, hasError }: AssigneeMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [])

  function toggle(name: string) {
    if (value.includes(name)) {
      onChange(value.filter(n => n !== name))
    } else {
      onChange([...value, name])
    }
  }

  const displayText = value.length > 0 ? value.join(', ') : '— unassigned —'
  const borderClass = hasError ? 'border-red-500 bg-red-50' : 'border-slate-200'

  return (
    <div ref={ref} className="relative">
      <div
        className={`border rounded px-1 py-0.5 text-xs w-full cursor-pointer truncate ${borderClass}`}
        onClick={() => setOpen(o => !o)}
        title={value.length > 0 ? value.join(', ') : undefined}
      >
        {displayText}
      </div>
      {open && (
        <div className="absolute z-10 top-full left-0 mt-0.5 bg-white border border-slate-200 rounded shadow-md min-w-[160px] max-h-48 overflow-y-auto">
          {members.length === 0 && (
            <div className="px-2 py-1 text-xs text-slate-400">No members</div>
          )}
          {members.map(m => (
            <label key={m.id} className="flex items-center gap-1.5 px-2 py-1 hover:bg-slate-50 cursor-pointer text-xs">
              <input
                type="checkbox"
                checked={value.includes(m.name)}
                onChange={() => toggle(m.name)}
              />
              {m.name}
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Replace the per-row assignee stub with `AssigneeMultiSelect`**

Find the stub `<div>` added in Task 6 Step 2 and replace with:
```tsx
<td className="p-1 border border-slate-200">
  <AssigneeMultiSelect
    value={task.assignee_names}
    members={members}
    onChange={(names) => update(task.row_id, { assignee_names: names })}
    hasError={errorMap[task.row_id]?.has('assignee_names')}
  />
</td>
```

- [ ] **Step 3: Replace the bulk assignee stub with `AssigneeMultiSelect` + implement `applyBulkAssignees`**

Replace the stub `<span>` in the bulk toolbar with:
```tsx
<AssigneeMultiSelect
  value={bulkAssignees}
  members={members}
  onChange={(names) => {
    if (names.length > 0) applyBulkAssignees(names)
  }}
/>
```

Replace the stub `applyBulkAssignees` function with the real implementation. Note: pass `names` as a parameter so we don't close over stale state:
```ts
function applyBulkAssignees(names: string[]) {
  if (names.length === 0) return
  onChange(tasks.map(t =>
    selectedIds.has(t.row_id)
      ? { ...t, assignee_names: [...new Set([...t.assignee_names, ...names])] }
      : t
  ))
  setBulkAssignees([])
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 5: Smoke test in the browser**

1. Open http://localhost:5173
2. Select a project
3. Extract or manually add a task
4. Click the assignee cell — verify the dropdown opens with member checkboxes
5. Select two members — verify the cell shows `Alice, Bob`
6. Select two rows via checkboxes — verify the bulk toolbar's assignee multi-select appears
7. Select an assignee in bulk — verify it merges into selected rows without removing existing assignees
8. Export CSV — verify the `assignee_names` column shows semicolon-separated values

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TaskTable.tsx
git commit -m "feat: add AssigneeMultiSelect component with bulk merge support"
```

---

## Task 8: Run full test suite and verify

**Files:** none

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && pytest tests/ -v
```

Expected: all PASS, 0 failures.

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Final smoke test — push to Zoho**

1. Open http://localhost:5173
2. Extract tasks from a short SOW snippet
3. Assign two members to one task
4. Push to Zoho
5. Verify in Zoho Projects that the task shows both members as owners

- [ ] **Step 4: Commit if any cleanup was needed**

```bash
git add -p
git commit -m "chore: post-integration cleanup"
```
