# SOW Task Generator Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app that extracts structured tasks from SOW documents using Claude AI and pushes them directly to Zoho Projects.

**Architecture:** React frontend calls a FastAPI backend. Backend handles all AI (Claude) and external API calls (Zoho, Google). Frontend provides editable task table with per-row client UUIDs for result mapping.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui (frontend); Python 3.11 + FastAPI + httpx + anthropic SDK (backend); Zoho Projects API, Google Drive export API.

---

## File Structure

```
sow-task-generator/
├── CLAUDE.md
├── .gitignore                       # root: ignores backend secrets + frontend build artifacts
├── docs/
│   └── superpowers/
│       ├── specs/2026-03-16-sow-task-generator-design.md
│       └── plans/2026-03-16-sow-task-generator.md
├── backend/
│   ├── main.py                      # FastAPI app, CORS, router registration
│   ├── requirements.txt
│   ├── .env.example
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── zoho_client.py           # OAuth token management + all Zoho API calls
│   │   ├── claude_client.py         # Anthropic SDK task extraction wrapper
│   │   └── google_client.py         # Google Drive export API wrapper
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── zoho_router.py           # GET /zoho/projects, /members, /milestones
│   │   ├── extract_router.py        # POST /extract
│   │   ├── push_router.py           # POST /push (two-pass, best-effort)
│   │   └── google_router.py         # GET /google-doc
│   ├── models/
│   │   ├── __init__.py
│   │   └── task.py                  # Pydantic models for all request/response types
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py              # Shared fixtures, app client
│       ├── test_task_models.py      # Pydantic model validation
│       ├── test_zoho_client.py      # Zoho client unit tests (mocked HTTP)
│       ├── test_claude_client.py    # Claude client unit tests (mocked SDK)
│       ├── test_google_client.py    # Google client unit tests (mocked HTTP)
│       ├── test_zoho_router.py      # /zoho/* endpoint tests
│       ├── test_extract_router.py   # /extract endpoint tests
│       ├── test_push_router.py      # /push endpoint tests
│       └── test_google_router.py    # /google-doc endpoint tests
└── frontend/
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.node.json
    ├── package.json
    ├── tailwind.config.ts
    ├── postcss.config.js
    ├── components.json              # shadcn/ui config
    ├── .env.example
    └── src/
        ├── main.tsx
        ├── App.tsx                  # Root component, top-level state
        ├── api/
        │   └── client.ts            # Typed fetch wrappers for all backend endpoints
        ├── types/
        │   └── task.ts              # TypeScript interfaces matching backend models
        ├── utils/
        │   └── validation.ts        # Push pre-flight validation logic
        ├── hooks/
        │   ├── useZohoProjects.ts   # Fetches project list on mount
        │   ├── useProjectMembers.ts # Fetches members when project selected
        │   └── useProjectMilestones.ts # Fetches milestones when project selected
        └── components/
            ├── ProjectSelector.tsx  # Project dropdown
            ├── InputPanel.tsx       # Text paste / Google Doc URL toggle
            ├── TaskTable.tsx        # Editable task table with inline edit/add/delete
            └── FeedbackPanel.tsx    # Per-task push results
```

---

## Chunk 1: Project Scaffolding

### Task 1: Initialize backend

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/main.py`
- Create: `backend/clients/__init__.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/models/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create backend directory structure**

```bash
cd /c/Users/aesha/projects/sow-task-generator
mkdir -p backend/clients backend/routers backend/models backend/tests
touch backend/clients/__init__.py backend/routers/__init__.py backend/models/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
anthropic==0.34.2
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
```

Save to `backend/requirements.txt`.

- [ ] **Step 3: Write .env.example**

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
ZOHO_CLIENT_ID=your_zoho_client_id
ZOHO_CLIENT_SECRET=your_zoho_client_secret
ZOHO_REFRESH_TOKEN=your_zoho_refresh_token
ZOHO_PORTAL_ID=your_zoho_portal_id
GOOGLE_API_KEY=your_google_api_key
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Save to `backend/.env.example`.

- [ ] **Step 4: Write backend .gitignore**

```
.env
zoho_token.json
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

Save to `backend/.gitignore`.

- [ ] **Step 5: Write main.py**

The app has exactly four routers: zoho_router, extract_router, push_router, google_router.

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers.zoho_router import router as zoho_router
from routers.extract_router import router as extract_router
from routers.push_router import router as push_router
from routers.google_router import router as google_router

load_dotenv()

app = FastAPI(title="SOW Task Generator")

origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(zoho_router)
app.include_router(extract_router)
app.include_router(push_router)
app.include_router(google_router)
```

- [ ] **Step 6: Write stub routers so main.py imports succeed**

Create each of the four router files with a minimal stub:

`backend/routers/zoho_router.py`:
```python
from fastapi import APIRouter
router = APIRouter(prefix="/zoho")
```

`backend/routers/extract_router.py`:
```python
from fastapi import APIRouter
router = APIRouter()
```

`backend/routers/push_router.py`:
```python
from fastapi import APIRouter
router = APIRouter()
```

`backend/routers/google_router.py`:
```python
from fastapi import APIRouter
router = APIRouter()
```

- [ ] **Step 7: Install dependencies and verify server starts**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Expected output: `INFO: Application startup complete.`

Stop the server (Ctrl+C).

- [ ] **Step 8: Commit**

```bash
cd ..
git init
git add backend/
git commit -m "feat: scaffold backend with FastAPI + CORS + stub routers"
```

---

### Task 2: Initialize frontend

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/.env.example`

- [ ] **Step 1: Scaffold Vite + React + TypeScript project**

```bash
cd /c/Users/aesha/projects/sow-task-generator
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Install Tailwind CSS**

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Update `tailwind.config.ts`:
```ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
} satisfies Config
```

Replace contents of `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 3: Install shadcn/ui**

```bash
npx shadcn@latest init
```

When prompted: Style=Default, Base color=Slate, CSS variables=Yes.

```bash
npx shadcn@latest add button select table input badge
```

- [ ] **Step 4: Install additional dependencies**

```bash
npm install uuid
npm install -D @types/uuid
```

- [ ] **Step 5: Write frontend .env.example**

```env
VITE_API_BASE_URL=http://localhost:8000
```

Save to `frontend/.env.example`. Copy to `frontend/.env`.

- [ ] **Step 6: Verify frontend starts**

```bash
npm run dev
```

Expected: Vite dev server running at `http://localhost:5173`. Open browser — React logo renders.

Stop the server.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold frontend with Vite + React + Tailwind + shadcn"
```

---

### Task 3: Root .gitignore

**Files:**
- Create: `/.gitignore`

- [ ] **Step 1: Write root .gitignore**

```
# Backend
backend/.env
backend/zoho_token.json
backend/.venv/
backend/__pycache__/
backend/*.pyc
backend/.pytest_cache/

# Frontend
frontend/.env
frontend/node_modules/
frontend/dist/
```

Save to `/c/Users/aesha/projects/sow-task-generator/.gitignore`.

> **Note:** Verify `zoho_token.json` is not already tracked: `git ls-files backend/zoho_token.json`. If it returns a path, run `git rm --cached backend/zoho_token.json` before committing.

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add root .gitignore"
```

---

## Chunk 2: Backend Data Models

### Task 4: Pydantic models

**Files:**
- Create: `backend/models/task.py`
- Create: `backend/tests/test_task_models.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_task_models.py`:

```python
import pytest
from pydantic import ValidationError
from models.task import Task, PushTask, ExtractRequest, ExtractResponse, PushRequest, PushTaskResult, PushResponse


class TestTask:
    def test_minimal_valid_task(self):
        task = Task(
            task_name="Set up repo",
            description="Initialize the project repository",
            estimated_hours=2.0,
            billing_type="billable",
        )
        assert task.task_name == "Set up repo"
        assert task.assignee_name is None
        assert task.sprint_milestone is None
        assert task.priority is None
        assert task.dependencies == []
        assert task.start_date is None
        assert task.end_date is None

    def test_full_valid_task(self):
        task = Task(
            task_name="Build API",
            description="Implement REST endpoints",
            assignee_name="Alice",
            estimated_hours=8.0,
            billing_type="non-billable",
            sprint_milestone="Sprint 1",
            priority="high",
            dependencies=["Set up repo"],
            start_date="2026-03-17",
            end_date="2026-03-20",
        )
        assert task.billing_type == "non-billable"
        assert task.priority == "high"

    def test_estimated_hours_at_minimum_boundary(self):
        task = Task(task_name="X", description="Y", estimated_hours=0.5, billing_type="billable")
        assert task.estimated_hours == 0.5

    def test_estimated_hours_at_maximum_boundary(self):
        task = Task(task_name="X", description="Y", estimated_hours=999, billing_type="billable")
        assert task.estimated_hours == 999

    def test_estimated_hours_below_minimum_raises(self):
        with pytest.raises(ValidationError, match="estimated_hours"):
            Task(task_name="X", description="Y", estimated_hours=0.4, billing_type="billable")

    def test_estimated_hours_above_maximum_raises(self):
        with pytest.raises(ValidationError, match="estimated_hours"):
            Task(task_name="X", description="Y", estimated_hours=1000, billing_type="billable")

    def test_invalid_billing_type_raises(self):
        with pytest.raises(ValidationError):
            Task(task_name="X", description="Y", estimated_hours=1.0, billing_type="maybe")

    def test_invalid_priority_raises(self):
        with pytest.raises(ValidationError):
            Task(task_name="X", description="Y", estimated_hours=1.0, billing_type="billable", priority="urgent")

    def test_end_date_before_start_date_raises(self):
        with pytest.raises(ValidationError, match="end_date"):
            Task(
                task_name="X", description="Y", estimated_hours=1.0, billing_type="billable",
                start_date="2026-03-20", end_date="2026-03-17",
            )

    def test_end_date_equals_start_date_is_valid(self):
        task = Task(
            task_name="X", description="Y", estimated_hours=1.0, billing_type="billable",
            start_date="2026-03-17", end_date="2026-03-17",
        )
        assert task.end_date == "2026-03-17"

    def test_missing_task_name_raises(self):
        with pytest.raises(ValidationError):
            Task(description="Y", estimated_hours=1.0, billing_type="billable")

    def test_missing_description_raises(self):
        with pytest.raises(ValidationError):
            Task(task_name="X", estimated_hours=1.0, billing_type="billable")

    def test_missing_estimated_hours_raises(self):
        with pytest.raises(ValidationError):
            Task(task_name="X", description="Y", billing_type="billable")


class TestPushTask:
    def test_push_task_requires_row_id(self):
        with pytest.raises(ValidationError):
            PushTask(task_name="X", description="Y", estimated_hours=1.0, billing_type="billable")

    def test_push_task_row_id_is_string(self):
        task = PushTask(
            row_id="uuid-abc-123",
            task_name="X", description="Y", estimated_hours=1.0, billing_type="billable",
        )
        assert task.row_id == "uuid-abc-123"


class TestExtractRequest:
    def test_valid_request(self):
        req = ExtractRequest(sow_text="Build a thing", team_members=["Alice", "Bob"])
        assert req.team_members == ["Alice", "Bob"]

    def test_empty_team_members_allowed(self):
        req = ExtractRequest(sow_text="Build a thing", team_members=[])
        assert req.team_members == []

    def test_sow_text_over_limit_raises(self):
        with pytest.raises(ValidationError):
            ExtractRequest(sow_text="x" * 50_001, team_members=[])

    def test_sow_text_at_limit_is_valid(self):
        req = ExtractRequest(sow_text="x" * 50_000, team_members=[])
        assert len(req.sow_text) == 50_000


class TestPushRequest:
    def test_valid_push_request(self):
        req = PushRequest(
            project_id="proj123",
            tasks=[{
                "row_id": "uuid-1",
                "task_name": "T1",
                "description": "Desc",
                "estimated_hours": 2.0,
                "billing_type": "billable",
            }],
        )
        assert req.tasks[0].row_id == "uuid-1"

    def test_missing_project_id_raises(self):
        with pytest.raises(ValidationError):
            PushRequest(tasks=[])


class TestPushTaskResult:
    def test_created_result(self):
        result = PushTaskResult(
            row_id="uuid-1", task_name="T1", status="created",
            zoho_task_id="zoho-123", warnings=[], error=None,
        )
        assert result.status == "created"

    def test_failed_result(self):
        result = PushTaskResult(
            row_id="uuid-1", task_name="T1", status="failed",
            zoho_task_id=None, warnings=[], error="Zoho API error",
        )
        assert result.error == "Zoho API error"
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd backend
source .venv/Scripts/activate
pytest tests/test_task_models.py -v
```

Expected: `ImportError: cannot import name 'Task' from 'models.task'`

- [ ] **Step 3: Write models/task.py**

```python
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


BillingType = Literal["billable", "non-billable"]
Priority = Literal["high", "medium", "low"]
TaskStatus = Literal["created", "failed", "warning"]


class Task(BaseModel):
    task_name: str
    description: str
    assignee_name: Optional[str] = None
    estimated_hours: float = Field(..., ge=0.5, le=999)
    billing_type: BillingType
    sprint_milestone: Optional[str] = None
    priority: Optional[Priority] = None
    dependencies: list[str] = Field(default_factory=list)
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD

    @model_validator(mode="after")
    def validate_dates(self) -> Task:
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be >= start_date")
        return self


class PushTask(Task):
    row_id: str


class ExtractRequest(BaseModel):
    sow_text: str = Field(..., max_length=50_000)
    team_members: list[str] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    tasks: list[Task]


class PushRequest(BaseModel):
    project_id: str
    tasks: list[PushTask]


class PushTaskResult(BaseModel):
    row_id: str
    task_name: str
    status: TaskStatus
    zoho_task_id: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class PushResponse(BaseModel):
    results: list[PushTaskResult]
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_task_models.py -v
```

Expected: All 17 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models/task.py backend/tests/test_task_models.py
git commit -m "feat: add Pydantic models for task, extract, and push"
```

---

## Chunk 3: Zoho Client

### Task 5: ZohoClient — token management and API methods

**Files:**
- Create: `backend/clients/zoho_client.py`
- Create: `backend/tests/test_zoho_client.py`

- [ ] **Step 1: Write failing tests for token management**

Create `backend/tests/test_zoho_client.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from clients.zoho_client import ZohoClient, TOKEN_URL


@pytest.fixture
def zoho_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ZOHO_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("ZOHO_REFRESH_TOKEN", "initial_refresh_token")
    monkeypatch.setenv("ZOHO_PORTAL_ID", "portal_123")
    return tmp_path


class TestTokenManagement:
    def test_token_url_is_zoho_oauth_endpoint(self):
        assert TOKEN_URL == "https://accounts.zoho.com/oauth/v2/token"

    def test_loads_token_from_env_when_no_file(self, zoho_env, monkeypatch):
        token_path = zoho_env / "zoho_token.json"
        monkeypatch.setattr("clients.zoho_client.TOKEN_FILE", str(token_path))
        client = ZohoClient()
        assert client._refresh_token == "initial_refresh_token"

    def test_loads_token_from_file_when_exists(self, zoho_env, monkeypatch):
        token_path = zoho_env / "zoho_token.json"
        token_path.write_text(json.dumps({"refresh_token": "file_refresh_token"}))
        monkeypatch.setattr("clients.zoho_client.TOKEN_FILE", str(token_path))
        client = ZohoClient()
        assert client._refresh_token == "file_refresh_token"

    def test_refresh_saves_new_token_to_file(self, zoho_env, monkeypatch):
        token_path = zoho_env / "zoho_token.json"
        monkeypatch.setattr("clients.zoho_client.TOKEN_FILE", str(token_path))
        client = ZohoClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
        }
        mock_response.raise_for_status = MagicMock()
        with patch.object(client._http, "post", return_value=mock_response):
            token = client._get_access_token()
        assert token == "new_access_token"
        assert client._refresh_token == "new_refresh_token"
        saved = json.loads(token_path.read_text())
        assert saved["refresh_token"] == "new_refresh_token"

    def test_refresh_raises_on_missing_access_token(self, zoho_env, monkeypatch):
        token_path = zoho_env / "zoho_token.json"
        monkeypatch.setattr("clients.zoho_client.TOKEN_FILE", str(token_path))
        client = ZohoClient()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_grant"}
        mock_response.raise_for_status = MagicMock()
        with patch.object(client._http, "post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="Failed to refresh Zoho token"):
                client._get_access_token()


@pytest.fixture
def zoho_client(zoho_env, monkeypatch):
    token_path = zoho_env / "zoho_token.json"
    monkeypatch.setattr("clients.zoho_client.TOKEN_FILE", str(token_path))
    c = ZohoClient()
    c._get_access_token = MagicMock(return_value="test_access_token")
    return c


class TestZohoApiMethods:
    def test_get_projects_returns_mapped_list(self, zoho_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "projects": [{"id_string": "p1", "name": "Project Alpha"}]
        }
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "get", return_value=mock_response):
            projects = zoho_client.get_projects()
        assert projects == [{"id_string": "p1", "name": "Project Alpha"}]

    def test_get_projects_returns_empty_list_on_missing_key(self, zoho_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "get", return_value=mock_response):
            assert zoho_client.get_projects() == []

    def test_get_members_returns_users(self, zoho_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"users": [{"id": "u1", "full_name": "Alice"}]}
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "get", return_value=mock_response):
            members = zoho_client.get_members("proj_1")
        assert members == [{"id": "u1", "full_name": "Alice"}]

    def test_get_milestones_returns_list(self, zoho_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"milestones": [{"id_string": "m1", "name": "Sprint 1"}]}
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "get", return_value=mock_response):
            milestones = zoho_client.get_milestones("proj_1")
        assert milestones == [{"id_string": "m1", "name": "Sprint 1"}]

    def test_create_task_returns_first_task(self, zoho_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"tasks": [{"id_string": "t1", "name": "My Task"}]}
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "post", return_value=mock_response):
            task = zoho_client.create_task("proj_1", {"name": "My Task"})
        assert task["id_string"] == "t1"

    def test_create_task_raises_when_no_tasks_in_response(self, zoho_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"tasks": []}
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "{}"
        with patch.object(zoho_client._http, "post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="no tasks"):
                zoho_client.create_task("proj_1", {"name": "My Task"})

    def test_add_dependency_posts_to_correct_url(self, zoho_client, monkeypatch):
        monkeypatch.setattr("clients.zoho_client.ZOHO_BASE", "https://projectsapi.zoho.com/restapi/portal/portal_123")
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "post", return_value=mock_response) as mock_post:
            zoho_client.add_dependency("proj_1", "task_A", "task_B")
        call_url = mock_post.call_args[0][0]
        assert "proj_1" in call_url
        assert "task_A" in call_url
        assert "dependency" in call_url

    def test_add_dependency_sends_correct_payload(self, zoho_client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch.object(zoho_client._http, "post", return_value=mock_response) as mock_post:
            zoho_client.add_dependency("proj_1", "task_A", "task_B")
        call_data = mock_post.call_args[1]["data"]
        assert call_data["depend_on_id"] == "task_B"
        assert call_data["type"] == "finish-to-start"
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_zoho_client.py -v
```

Expected: `ImportError: cannot import name 'ZohoClient'`

- [ ] **Step 3: Write clients/zoho_client.py**

```python
import json
import os
from pathlib import Path
import httpx

TOKEN_FILE = str(Path(__file__).parent.parent / "zoho_token.json")
TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_PORTAL_ID = os.getenv("ZOHO_PORTAL_ID", "")
ZOHO_BASE = f"https://projectsapi.zoho.com/restapi/portal/{ZOHO_PORTAL_ID}"


class ZohoClient:
    def __init__(self):
        self._client_id = os.getenv("ZOHO_CLIENT_ID", "")
        self._client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
        self._refresh_token = self._load_refresh_token()
        self._http = httpx.Client(timeout=30.0)

    def _load_refresh_token(self) -> str:
        if Path(TOKEN_FILE).exists():
            data = json.loads(Path(TOKEN_FILE).read_text())
            return data.get("refresh_token", "")
        return os.getenv("ZOHO_REFRESH_TOKEN", "")

    def _save_refresh_token(self, token: str) -> None:
        Path(TOKEN_FILE).write_text(json.dumps({"refresh_token": token}))

    def _get_access_token(self) -> str:
        response = self._http.post(TOKEN_URL, data={
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
        })
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise RuntimeError(f"Failed to refresh Zoho token: {data}")
        new_refresh = data.get("refresh_token")
        if new_refresh:
            self._refresh_token = new_refresh
            self._save_refresh_token(new_refresh)
        return access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Zoho-oauthtoken {self._get_access_token()}"}

    def get_projects(self) -> list[dict]:
        url = f"{ZOHO_BASE}/projects/?status=active"
        response = self._http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get("projects", [])

    def get_members(self, project_id: str) -> list[dict]:
        url = f"{ZOHO_BASE}/projects/{project_id}/users/"
        response = self._http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get("users", [])

    def get_milestones(self, project_id: str) -> list[dict]:
        url = f"{ZOHO_BASE}/projects/{project_id}/milestones/"
        response = self._http.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json().get("milestones", [])

    def create_task(self, project_id: str, payload: dict) -> dict:
        url = f"{ZOHO_BASE}/projects/{project_id}/tasks/"
        response = self._http.post(url, headers=self._headers(), data=payload)
        response.raise_for_status()
        tasks = response.json().get("tasks", [])
        if not tasks:
            raise RuntimeError(f"Zoho task creation returned no tasks: {response.text}")
        return tasks[0]

    def add_dependency(self, project_id: str, task_id: str, depends_on_id: str) -> None:
        url = f"{ZOHO_BASE}/projects/{project_id}/tasks/{task_id}/dependency/"
        response = self._http.post(url, headers=self._headers(), data={
            "depend_on_id": depends_on_id,
            "type": "finish-to-start",
        })
        response.raise_for_status()
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_zoho_client.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/clients/zoho_client.py backend/tests/test_zoho_client.py
git commit -m "feat: add ZohoClient with OAuth token rotation and Zoho API methods"
```

---

## Chunk 4: Google and Claude Clients

### Task 6: Google client

**Files:**
- Create: `backend/clients/google_client.py`
- Create: `backend/tests/test_google_client.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_google_client.py`:

```python
import pytest
import httpx
from unittest.mock import MagicMock, patch
from clients.google_client import GoogleClient, extract_doc_id


class TestExtractDocId:
    def test_extracts_id_from_edit_url(self):
        url = "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit"
        assert extract_doc_id(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"

    def test_extracts_id_from_view_url(self):
        url = "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/view"
        assert extract_doc_id(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"

    def test_returns_none_for_non_google_doc_url(self):
        assert extract_doc_id("https://example.com/doc") is None

    def test_returns_none_for_empty_string(self):
        assert extract_doc_id("") is None


class TestGoogleClient:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test_api_key")
        return GoogleClient()

    def test_fetch_doc_returns_plain_text(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "This is the document text."
        mock_response.raise_for_status = MagicMock()
        with patch.object(client._http, "get", return_value=mock_response):
            text = client.fetch_doc("https://docs.google.com/document/d/abc123/edit")
        assert text == "This is the document text."

    def test_fetch_doc_uses_drive_export_api(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "content"
        mock_response.raise_for_status = MagicMock()
        with patch.object(client._http, "get", return_value=mock_response) as mock_get:
            client.fetch_doc("https://docs.google.com/document/d/abc123/edit")
        called_url = mock_get.call_args[0][0]
        assert "drive/v3/files/abc123/export" in called_url
        assert "mimeType=text/plain" in called_url
        assert "key=test_api_key" in called_url

    def test_fetch_doc_raises_value_error_on_invalid_url(self, client):
        with pytest.raises(ValueError, match="Invalid Google Docs URL"):
            client.fetch_doc("https://example.com/not-a-doc")

    def test_fetch_doc_raises_permission_error_on_403(self, client):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403", request=MagicMock(), response=mock_response
        )
        with patch.object(client._http, "get", return_value=mock_response):
            with pytest.raises(PermissionError, match="not publicly accessible"):
                client.fetch_doc("https://docs.google.com/document/d/abc123/edit")
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_google_client.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write clients/google_client.py**

```python
import os
import re
import httpx


def extract_doc_id(url: str) -> str | None:
    match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


class GoogleClient:
    def __init__(self):
        self._api_key = os.getenv("GOOGLE_API_KEY", "")
        self._http = httpx.Client(timeout=30.0)

    def fetch_doc(self, url: str) -> str:
        doc_id = extract_doc_id(url)
        if not doc_id:
            raise ValueError(f"Invalid Google Docs URL: {url}")
        export_url = (
            f"https://www.googleapis.com/drive/v3/files/{doc_id}/export"
            f"?mimeType=text/plain&key={self._api_key}"
        )
        try:
            response = self._http.get(export_url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise PermissionError(
                    "Google Doc is not publicly accessible. Share it with 'Anyone with the link'."
                )
            raise
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_google_client.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/clients/google_client.py backend/tests/test_google_client.py
git commit -m "feat: add GoogleClient using Google Drive export API"
```

---

### Task 7: Claude client

**Files:**
- Create: `backend/clients/claude_client.py`
- Create: `backend/tests/test_claude_client.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_claude_client.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from clients.claude_client import ClaudeClient, SYSTEM_PROMPT, MODEL


class TestSystemPrompt:
    def test_prompt_contains_all_required_fields(self):
        for field in ["task_name", "description", "assignee_name", "estimated_hours",
                      "billing_type", "sprint_milestone", "priority", "dependencies",
                      "start_date", "end_date"]:
            assert field in SYSTEM_PROMPT, f"SYSTEM_PROMPT missing field: {field}"

    def test_prompt_specifies_json_only_output(self):
        assert "JSON" in SYSTEM_PROMPT

    def test_prompt_specifies_estimated_hours_default(self):
        assert "1.0" in SYSTEM_PROMPT

    def test_prompt_specifies_billing_type_default(self):
        assert "billable" in SYSTEM_PROMPT

    def test_model_constant_is_correct(self):
        assert MODEL == "claude-sonnet-4-6"


class TestClaudeClient:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")
        return ClaudeClient()

    def _make_mock_message(self, payload: dict) -> MagicMock:
        mock_content = MagicMock()
        mock_content.text = json.dumps(payload)
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        return mock_message

    def test_extract_tasks_returns_parsed_tasks(self, client):
        tasks_payload = [{
            "task_name": "Set up CI",
            "description": "Configure GitHub Actions",
            "assignee_name": "Alice",
            "estimated_hours": 3.0,
            "billing_type": "billable",
            "sprint_milestone": None,
            "priority": "high",
            "dependencies": [],
            "start_date": None,
            "end_date": None,
        }]
        mock_messages = MagicMock()
        mock_messages.create.return_value = self._make_mock_message({"tasks": tasks_payload})
        with patch.object(client._anthropic, "messages", mock_messages):
            result = client.extract_tasks("Build a CI pipeline", ["Alice", "Bob"])
        assert len(result) == 1
        assert result[0]["task_name"] == "Set up CI"

    def test_extract_tasks_passes_team_members_in_prompt(self, client):
        mock_messages = MagicMock()
        mock_messages.create.return_value = self._make_mock_message({"tasks": []})
        with patch.object(client._anthropic, "messages", mock_messages):
            client.extract_tasks("Some SOW", ["Alice", "Bob"])
        user_message = mock_messages.create.call_args[1]["messages"][0]["content"]
        assert "Alice" in user_message
        assert "Bob" in user_message

    def test_extract_tasks_uses_correct_model(self, client):
        mock_messages = MagicMock()
        mock_messages.create.return_value = self._make_mock_message({"tasks": []})
        with patch.object(client._anthropic, "messages", mock_messages):
            client.extract_tasks("SOW text", [])
        assert mock_messages.create.call_args[1]["model"] == MODEL

    def test_extract_tasks_raises_on_invalid_json(self, client):
        mock_content = MagicMock()
        mock_content.text = "Not valid JSON at all"
        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_messages = MagicMock()
        mock_messages.create.return_value = mock_message
        with patch.object(client._anthropic, "messages", mock_messages):
            with pytest.raises(ValueError, match="parse_failed"):
                client.extract_tasks("Build something", [])

    def test_extract_tasks_raises_on_missing_tasks_key(self, client):
        mock_messages = MagicMock()
        mock_messages.create.return_value = self._make_mock_message({"result": []})
        with patch.object(client._anthropic, "messages", mock_messages):
            with pytest.raises(ValueError, match="parse_failed"):
                client.extract_tasks("Build something", [])
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_claude_client.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write clients/claude_client.py**

```python
import json
import os
import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a project task extractor. Given a Statement of Work (SOW) or WBS document, extract all tasks and return ONLY valid JSON — no prose, no markdown, no code fences.

Return a JSON object with a single key "tasks" containing an array of task objects. Each task object must match this exact schema:
{
  "task_name": string,
  "description": string,
  "assignee_name": string|null,
  "estimated_hours": number,
  "billing_type": "billable"|"non-billable",
  "sprint_milestone": string|null,
  "priority": "high"|"medium"|"low"|null,
  "dependencies": [string],
  "start_date": "YYYY-MM-DD"|null,
  "end_date": "YYYY-MM-DD"|null
}

Rules:
- estimated_hours must always be a number, never null. Default to 1.0 if not determinable.
- assignee_name must only be a name from the provided team_members list. Use null if no match.
- billing_type defaults to "billable" when not specified in the SOW.
- All other optional fields must be null if not determinable — never omit them.
"""


class ClaudeClient:
    def __init__(self):
        self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    def extract_tasks(self, sow_text: str, team_members: list[str]) -> list[dict]:
        user_message = f"Team members: {team_members}\n\nSOW:\n{sow_text}"
        message = self._anthropic.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text
        try:
            data = json.loads(raw)
            if "tasks" not in data:
                raise KeyError("missing 'tasks' key")
            return data["tasks"]
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"parse_failed: {e}") from e
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_claude_client.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/clients/claude_client.py backend/tests/test_claude_client.py
git commit -m "feat: add ClaudeClient for SOW task extraction"
```

---

## Chunk 5: Backend Routers

### Task 8: Shared test fixtures and Zoho router

**Files:**
- Create: `backend/tests/conftest.py`
- Modify: `backend/routers/zoho_router.py`
- Create: `backend/tests/test_zoho_router.py`

- [ ] **Step 1: Write conftest.py**

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def app_client():
    from main import app
    return TestClient(app)
```

- [ ] **Step 2: Verify fixtures import cleanly**

```bash
pytest tests/conftest.py --collect-only
```

Expected: No collection errors.

- [ ] **Step 3: Write failing tests for Zoho router**

Create `backend/tests/test_zoho_router.py`:

```python
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


@pytest.fixture
def client():
    with patch("routers.zoho_router.ZohoClient") as MockZoho:
        instance = MagicMock()
        instance.get_projects.return_value = [{"id_string": "p1", "name": "Alpha"}]
        instance.get_members.return_value = [{"id": "u1", "full_name": "Alice"}]
        instance.get_milestones.return_value = [{"id_string": "m1", "name": "Sprint 1"}]
        MockZoho.return_value = instance
        from main import app
        yield TestClient(app)


def test_get_projects_returns_200(client):
    response = client.get("/zoho/projects")
    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == [{"id": "p1", "name": "Alpha"}]


def test_get_members_returns_200(client):
    response = client.get("/zoho/projects/p1/members")
    assert response.status_code == 200
    assert response.json()["members"] == [{"id": "u1", "name": "Alice"}]


def test_get_milestones_returns_200(client):
    response = client.get("/zoho/projects/p1/milestones")
    assert response.status_code == 200
    assert response.json()["milestones"] == [{"id": "m1", "name": "Sprint 1"}]


def test_get_projects_returns_503_on_zoho_error():
    with patch("routers.zoho_router.ZohoClient") as MockZoho:
        instance = MagicMock()
        instance.get_projects.side_effect = httpx.HTTPError("connection failed")
        MockZoho.return_value = instance
        from main import app
        response = TestClient(app).get("/zoho/projects")
    assert response.status_code == 503
```

- [ ] **Step 4: Run tests — confirm they fail**

```bash
pytest tests/test_zoho_router.py -v
```

Expected: 404 errors (router stubs have no routes).

- [ ] **Step 5: Write routers/zoho_router.py**

```python
import httpx
from fastapi import APIRouter, HTTPException
from clients.zoho_client import ZohoClient

router = APIRouter(prefix="/zoho")


@router.get("/projects")
def get_projects():
    try:
        client = ZohoClient()
        projects = client.get_projects()
        return {"projects": [{"id": p["id_string"], "name": p["name"]} for p in projects]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")


@router.get("/projects/{project_id}/members")
def get_members(project_id: str):
    try:
        client = ZohoClient()
        members = client.get_members(project_id)
        return {"members": [{"id": m["id"], "name": m["full_name"]} for m in members]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")


@router.get("/projects/{project_id}/milestones")
def get_milestones(project_id: str):
    try:
        client = ZohoClient()
        milestones = client.get_milestones(project_id)
        return {"milestones": [{"id": m["id_string"], "name": m["name"]} for m in milestones]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")
```

- [ ] **Step 6: Run tests — confirm they pass**

```bash
pytest tests/test_zoho_router.py -v
```

Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/conftest.py backend/routers/zoho_router.py backend/tests/test_zoho_router.py
git commit -m "feat: add Zoho router for projects, members, milestones"
```

---

### Task 9: Google and Extract routers

**Files:**
- Modify: `backend/routers/google_router.py`
- Create: `backend/tests/test_google_router.py`
- Modify: `backend/routers/extract_router.py`
- Create: `backend/tests/test_extract_router.py`

- [ ] **Step 1: Write failing tests for Google router**

Create `backend/tests/test_google_router.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from urllib.parse import quote


@pytest.fixture
def google_client_mock():
    with patch("routers.google_router.GoogleClient") as MockGoogle:
        instance = MagicMock()
        instance.fetch_doc.return_value = "SOW content here"
        MockGoogle.return_value = instance
        from main import app
        yield TestClient(app), instance


def test_fetch_doc_returns_200(google_client_mock):
    test_client, _ = google_client_mock
    url = quote("https://docs.google.com/document/d/abc123/edit", safe="")
    response = test_client.get(f"/google-doc?url={url}")
    assert response.status_code == 200
    assert response.json() == {"text": "SOW content here"}


def test_fetch_doc_returns_400_on_invalid_url(google_client_mock):
    test_client, mock_instance = google_client_mock
    mock_instance.fetch_doc.side_effect = ValueError("Invalid Google Docs URL")
    url = quote("https://example.com/not-a-doc", safe="")
    response = test_client.get(f"/google-doc?url={url}")
    assert response.status_code == 400


def test_fetch_doc_returns_403_on_private_doc(google_client_mock):
    test_client, mock_instance = google_client_mock
    mock_instance.fetch_doc.side_effect = PermissionError("not publicly accessible")
    url = quote("https://docs.google.com/document/d/private/edit", safe="")
    response = test_client.get(f"/google-doc?url={url}")
    assert response.status_code == 403
```

- [ ] **Step 2: Run Google router tests — confirm they fail**

```bash
pytest tests/test_google_router.py -v
```

Expected: 404 errors.

- [ ] **Step 3: Write routers/google_router.py**

```python
from fastapi import APIRouter, HTTPException, Query
from clients.google_client import GoogleClient

router = APIRouter()


@router.get("/google-doc")
def fetch_google_doc(url: str = Query(...)):
    try:
        client = GoogleClient()
        text = client.fetch_doc(url)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
```

- [ ] **Step 4: Run Google router tests — confirm they pass**

```bash
pytest tests/test_google_router.py -v
```

Expected: All PASS.

- [ ] **Step 5: Write failing tests for Extract router**

Create `backend/tests/test_extract_router.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


VALID_TASK = {
    "task_name": "Set up repo",
    "description": "Initialize project",
    "assignee_name": "Alice",
    "estimated_hours": 2.0,
    "billing_type": "billable",
    "sprint_milestone": None,
    "priority": None,
    "dependencies": [],
    "start_date": None,
    "end_date": None,
}


@pytest.fixture
def claude_mock():
    with patch("routers.extract_router.ClaudeClient") as MockClaude:
        instance = MagicMock()
        instance.extract_tasks.return_value = [VALID_TASK]
        MockClaude.return_value = instance
        from main import app
        yield TestClient(app), instance


def test_extract_returns_200_with_tasks(claude_mock):
    test_client, _ = claude_mock
    response = test_client.post(
        "/extract",
        json={"sow_text": "Build a CI pipeline", "team_members": ["Alice"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["task_name"] == "Set up repo"


def test_extract_returns_422_on_claude_parse_failure(claude_mock):
    test_client, mock_instance = claude_mock
    mock_instance.extract_tasks.side_effect = ValueError("parse_failed: invalid json")
    response = test_client.post(
        "/extract",
        json={"sow_text": "Some text", "team_members": []},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "parse_failed"
    assert "raw_response" in body


def test_extract_returns_422_on_oversized_input(claude_mock):
    test_client, _ = claude_mock
    response = test_client.post(
        "/extract",
        json={"sow_text": "x" * 50_001, "team_members": []},
    )
    assert response.status_code == 422


def test_extract_returns_422_on_missing_sow_text(claude_mock):
    test_client, _ = claude_mock
    response = test_client.post("/extract", json={"team_members": []})
    assert response.status_code == 422
```

- [ ] **Step 6: Run Extract router tests — confirm they fail**

```bash
pytest tests/test_extract_router.py -v
```

Expected: 404 errors.

- [ ] **Step 7: Write routers/extract_router.py**

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from clients.claude_client import ClaudeClient
from models.task import ExtractRequest, ExtractResponse

router = APIRouter()


@router.post("/extract")
def extract_tasks(request: ExtractRequest):
    try:
        client = ClaudeClient()
        raw_tasks = client.extract_tasks(request.sow_text, request.team_members)
        return ExtractResponse(tasks=raw_tasks)
    except ValueError as e:
        raw = str(e).replace("parse_failed: ", "", 1)
        return JSONResponse(
            status_code=422,
            content={"error": "parse_failed", "raw_response": raw},
        )
```

- [ ] **Step 8: Run Extract router tests — confirm they pass**

```bash
pytest tests/test_extract_router.py -v
```

Expected: All PASS.

- [ ] **Step 9: Run full test suite**

```bash
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/routers/google_router.py backend/tests/test_google_router.py \
        backend/routers/extract_router.py backend/tests/test_extract_router.py
git commit -m "feat: add Google Doc and Extract routers"
```

---

## Chunk 6: Push Router

### Task 10: Push router — two-pass task creation

**Files:**
- Modify: `backend/routers/push_router.py`
- Create: `backend/tests/test_push_router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_push_router.py`:

```python
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from routers.push_router import _resolve_assignee, _resolve_milestone


# --- Unit tests for resolver helpers ---

class TestResolveAssignee:
    def test_exact_match_returns_id(self):
        members = [{"id": "u1", "name": "Alice"}, {"id": "u2", "name": "Bob"}]
        user_id, warning = _resolve_assignee("Alice", members)
        assert user_id == "u1"
        assert warning is None

    def test_case_insensitive_match(self):
        members = [{"id": "u1", "name": "Alice"}]
        user_id, warning = _resolve_assignee("alice", members)
        assert user_id == "u1"

    def test_no_match_returns_warning(self):
        members = [{"id": "u1", "name": "Alice"}]
        user_id, warning = _resolve_assignee("Unknown", members)
        assert user_id is None
        assert "Unknown" in warning
        assert "assignee" in warning.lower()

    def test_none_assignee_returns_none_no_warning(self):
        user_id, warning = _resolve_assignee(None, [])
        assert user_id is None
        assert warning is None


class TestResolveMilestone:
    def test_exact_match_returns_id(self):
        milestones = [{"id": "m1", "name": "Sprint 1"}]
        ms_id, warning = _resolve_milestone("Sprint 1", milestones)
        assert ms_id == "m1"
        assert warning is None

    def test_case_insensitive_match(self):
        milestones = [{"id": "m1", "name": "Sprint 1"}]
        ms_id, warning = _resolve_milestone("sprint 1", milestones)
        assert ms_id == "m1"

    def test_no_match_returns_warning(self):
        milestones = [{"id": "m1", "name": "Sprint 1"}]
        ms_id, warning = _resolve_milestone("Sprint 99", milestones)
        assert ms_id is None
        assert "Sprint 99" in warning
        assert "milestone" in warning.lower()

    def test_none_milestone_returns_none_no_warning(self):
        ms_id, warning = _resolve_milestone(None, [])
        assert ms_id is None
        assert warning is None


# --- Integration tests for /push endpoint ---

def make_push_task(overrides=None):
    task = {
        "row_id": "row-1",
        "task_name": "Set up repo",
        "description": "Init project",
        "assignee_name": "Alice",
        "estimated_hours": 2.0,
        "billing_type": "billable",
        "sprint_milestone": None,
        "priority": None,
        "dependencies": [],
        "start_date": None,
        "end_date": None,
    }
    if overrides:
        task.update(overrides)
    return task


@pytest.fixture
def zoho_mock():
    with patch("routers.push_router.ZohoClient") as MockZoho:
        instance = MagicMock()
        instance.get_members.return_value = [{"id": "user-1", "name": "Alice"}]
        instance.get_milestones.return_value = [{"id": "ms-1", "name": "Sprint 1"}]
        instance.create_task.return_value = {"id_string": "zoho-task-1"}
        MockZoho.return_value = instance
        from main import app
        yield TestClient(app), instance


def test_push_creates_task_successfully(zoho_mock):
    test_client, _ = zoho_mock
    response = test_client.post(
        "/push",
        json={"project_id": "proj-1", "tasks": [make_push_task()]},
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["status"] == "created"
    assert results[0]["row_id"] == "row-1"
    assert results[0]["zoho_task_id"] == "zoho-task-1"


def test_push_warns_when_assignee_not_found(zoho_mock):
    test_client, _ = zoho_mock
    task = make_push_task({"assignee_name": "Unknown Person"})
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": [task]},
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "warning"
    assert any("assignee" in w.lower() for w in result["warnings"])


def test_push_warns_when_milestone_not_found(zoho_mock):
    test_client, _ = zoho_mock
    task = make_push_task({"sprint_milestone": "Nonexistent Sprint"})
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": [task]},
    )
    result = response.json()["results"][0]
    assert any("milestone" in w.lower() for w in result["warnings"])


def test_push_handles_task_creation_failure_independently(zoho_mock):
    test_client, mock_instance = zoho_mock
    mock_instance.create_task.side_effect = [
        Exception("Zoho error"),
        {"id_string": "zoho-task-2"},
    ]
    tasks = [
        make_push_task({"row_id": "row-1", "task_name": "Task A"}),
        make_push_task({"row_id": "row-2", "task_name": "Task B"}),
    ]
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": tasks},
    )
    results = response.json()["results"]
    assert results[0]["status"] == "failed"
    assert results[1]["status"] == "created"


def test_push_links_dependencies_in_second_pass(zoho_mock):
    test_client, mock_instance = zoho_mock
    mock_instance.create_task.side_effect = [
        {"id_string": "zoho-task-1"},
        {"id_string": "zoho-task-2"},
    ]
    tasks = [
        make_push_task({"row_id": "row-1", "task_name": "Task A", "dependencies": []}),
        make_push_task({"row_id": "row-2", "task_name": "Task B", "dependencies": ["Task A"]}),
    ]
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": tasks},
    )
    assert response.status_code == 200
    mock_instance.add_dependency.assert_called_once_with("proj-1", "zoho-task-2", "zoho-task-1")


def test_push_warns_when_dependency_source_failed(zoho_mock):
    test_client, mock_instance = zoho_mock
    mock_instance.create_task.side_effect = [
        Exception("Task A failed"),
        {"id_string": "zoho-task-2"},
    ]
    tasks = [
        make_push_task({"row_id": "row-1", "task_name": "Task A"}),
        make_push_task({"row_id": "row-2", "task_name": "Task B", "dependencies": ["Task A"]}),
    ]
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": tasks},
    )
    result_b = next(r for r in response.json()["results"] if r["row_id"] == "row-2")
    assert any("Task A" in w for w in result_b["warnings"])


def test_push_skips_dependency_linking_when_target_task_failed(zoho_mock):
    """If task B (the dependent) failed, skip second-pass dependency linking for it."""
    test_client, mock_instance = zoho_mock
    mock_instance.create_task.side_effect = [
        {"id_string": "zoho-task-1"},  # Task A succeeds
        Exception("Task B failed"),    # Task B fails
    ]
    tasks = [
        make_push_task({"row_id": "row-1", "task_name": "Task A", "dependencies": []}),
        make_push_task({"row_id": "row-2", "task_name": "Task B", "dependencies": ["Task A"]}),
    ]
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": tasks},
    )
    mock_instance.add_dependency.assert_not_called()


def test_push_returns_503_on_total_zoho_outage(zoho_mock):
    test_client, mock_instance = zoho_mock
    mock_instance.get_members.side_effect = httpx.HTTPError("connection refused")
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": [make_push_task()]},
    )
    assert response.status_code == 503


def test_push_returns_422_on_validation_error():
    from main import app
    task = make_push_task({"estimated_hours": 0.1})  # below minimum 0.5
    response = TestClient(app).post(
        "/push", json={"project_id": "proj-1", "tasks": [task]},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_push_router.py -v
```

Expected: `ImportError` for `_resolve_assignee` and 404 for router tests.

- [ ] **Step 3: Write routers/push_router.py**

```python
import httpx
from fastapi import APIRouter, HTTPException
from clients.zoho_client import ZohoClient
from models.task import PushRequest, PushResponse, PushTaskResult

router = APIRouter()

BILLING_MAP = {"billable": "1", "non-billable": "2"}
PRIORITY_MAP = {"high": "1", "medium": "2", "low": "3"}


def _resolve_assignee(
    assignee_name: str | None, members: list[dict]
) -> tuple[str | None, str | None]:
    """Returns (zoho_user_id, warning_message)."""
    if not assignee_name:
        return None, None
    for m in members:
        if m["name"].lower() == assignee_name.lower():
            return m["id"], None
    return (
        None,
        f"Assignee '{assignee_name}' not found in project members — task created without assignee",
    )


def _resolve_milestone(
    milestone_name: str | None, milestones: list[dict]
) -> tuple[str | None, str | None]:
    """Returns (zoho_milestone_id, warning_message)."""
    if not milestone_name:
        return None, None
    for m in milestones:
        if m["name"].lower() == milestone_name.lower():
            return m["id"], None
    return None, f"Milestone '{milestone_name}' not found in project — field dropped"


def _build_task_payload(task, assignee_id: str | None, milestone_id: str | None) -> dict:
    payload = {
        "name": task.task_name,
        "description": task.description,
        "duration": str(task.estimated_hours),
        "billing_type": BILLING_MAP[task.billing_type],
    }
    if assignee_id:
        payload["person_responsible"] = assignee_id
    if milestone_id:
        payload["milestone_id"] = milestone_id
    if task.priority:
        payload["priority"] = PRIORITY_MAP[task.priority]
    if task.start_date:
        payload["start_date"] = task.start_date
    if task.end_date:
        payload["end_date"] = task.end_date
    return payload


@router.post("/push", response_model=PushResponse)
def push_tasks(request: PushRequest):
    try:
        zoho = ZohoClient()
        members = zoho.get_members(request.project_id)
        milestones = zoho.get_milestones(request.project_id)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")

    results: list[PushTaskResult] = []
    name_to_zoho_id: dict[str, str] = {}

    # Pass 1: create all tasks independently
    for task in request.tasks:
        warnings = []
        assignee_id, aw = _resolve_assignee(task.assignee_name, members)
        if aw:
            warnings.append(aw)
        milestone_id, mw = _resolve_milestone(task.sprint_milestone, milestones)
        if mw:
            warnings.append(mw)
        try:
            payload = _build_task_payload(task, assignee_id, milestone_id)
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
        # Skip pass 2 entirely for tasks that failed in pass 1
        if not result or result.status == "failed":
            continue
        task_zoho_id = result.zoho_task_id
        for dep_name in task.dependencies:
            dep_zoho_id = name_to_zoho_id.get(dep_name)
            if not dep_zoho_id:
                result.warnings.append(
                    f"Dependency '{dep_name}' could not be linked: source task failed to create or was not found"
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

- [ ] **Step 4: Run push router tests — confirm they pass**

```bash
pytest tests/test_push_router.py -v
```

Expected: All PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/push_router.py backend/tests/test_push_router.py
git commit -m "feat: add push router with two-pass task creation and dependency linking"
```

---

## Chunk 7: Frontend Types, API Client, and Hooks

### Task 11: TypeScript types and API client

**Files:**
- Create: `frontend/src/types/task.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write src/types/task.ts**

```typescript
export type BillingType = 'billable' | 'non-billable'
export type Priority = 'high' | 'medium' | 'low'
export type TaskStatus = 'created' | 'failed' | 'warning'

// Sentinel value: when Claude cannot determine hours, it returns exactly 1.0.
// The backend always returns estimated_hours as a number (never null).
export const HOURS_SENTINEL = 1.0

export interface Task {
  row_id: string
  task_name: string
  description: string
  assignee_name: string | null
  estimated_hours: number
  billing_type: BillingType
  sprint_milestone: string | null
  priority: Priority | null
  dependencies: string[]
  start_date: string | null  // YYYY-MM-DD
  end_date: string | null    // YYYY-MM-DD
  _hours_defaulted?: boolean  // true when AI returned sentinel 1.0 — amber highlight in UI
}

export interface ZohoProject { id: string; name: string }
export interface ZohoMember { id: string; name: string }
export interface ZohoMilestone { id: string; name: string }

export interface ExtractRequest {
  sow_text: string
  team_members: string[]
}

export interface PushRequest {
  project_id: string
  tasks: Task[]
}

export interface PushTaskResult {
  row_id: string
  task_name: string
  status: TaskStatus
  zoho_task_id: string | null
  warnings: string[]
  error: string | null
}

export interface PushResponse {
  results: PushTaskResult[]
}
```

- [ ] **Step 2: Write src/api/client.ts**

```typescript
import type {
  ZohoProject, ZohoMember, ZohoMilestone,
  ExtractRequest, Task, PushRequest, PushResponse,
} from '../types/task'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const err = new Error(body.detail ?? `HTTP ${response.status}`) as Error & {
      status: number
      body: unknown
    }
    err.status = response.status
    err.body = body
    throw err
  }
  return response.json() as Promise<T>
}

export async function fetchProjects(): Promise<ZohoProject[]> {
  const data = await apiFetch<{ projects: ZohoProject[] }>('/zoho/projects')
  return data.projects
}

export async function fetchMembers(projectId: string): Promise<ZohoMember[]> {
  const data = await apiFetch<{ members: ZohoMember[] }>(`/zoho/projects/${projectId}/members`)
  return data.members
}

export async function fetchMilestones(projectId: string): Promise<ZohoMilestone[]> {
  const data = await apiFetch<{ milestones: ZohoMilestone[] }>(`/zoho/projects/${projectId}/milestones`)
  return data.milestones
}

export async function fetchGoogleDoc(url: string): Promise<string> {
  const encoded = encodeURIComponent(url)
  const data = await apiFetch<{ text: string }>(`/google-doc?url=${encoded}`)
  return data.text
}

export async function extractTasks(request: ExtractRequest): Promise<Task[]> {
  const data = await apiFetch<{ tasks: Task[] }>('/extract', {
    method: 'POST',
    body: JSON.stringify(request),
  })
  return data.tasks
}

export async function pushTasks(request: PushRequest): Promise<PushResponse> {
  return apiFetch<PushResponse>('/push', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add src/types/task.ts src/api/client.ts
git commit -m "feat: add TypeScript types and API client"
```

---

### Task 12: Data-fetching hooks and validation utility

**Files:**
- Create: `frontend/src/hooks/useZohoProjects.ts`
- Create: `frontend/src/hooks/useProjectMembers.ts`
- Create: `frontend/src/hooks/useProjectMilestones.ts`
- Create: `frontend/src/utils/validation.ts`

- [ ] **Step 1: Write useZohoProjects.ts**

```typescript
import { useState, useEffect } from 'react'
import type { ZohoProject } from '../types/task'
import { fetchProjects } from '../api/client'

export function useZohoProjects() {
  const [projects, setProjects] = useState<ZohoProject[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchProjects()
      .then((data) => { if (!cancelled) setProjects(data) })
      .catch((e) => { if (!cancelled) setError(e.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  return { projects, loading, error }
}
```

- [ ] **Step 2: Write useProjectMembers.ts**

```typescript
import { useState, useEffect } from 'react'
import type { ZohoMember } from '../types/task'
import { fetchMembers } from '../api/client'

export function useProjectMembers(projectId: string | null) {
  const [members, setMembers] = useState<ZohoMember[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) { setMembers([]); return }
    let cancelled = false
    setLoading(true)
    fetchMembers(projectId)
      .then((data) => { if (!cancelled) setMembers(data) })
      .catch(() => { if (!cancelled) setMembers([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId])

  return { members, loading }
}
```

- [ ] **Step 3: Write useProjectMilestones.ts**

```typescript
import { useState, useEffect } from 'react'
import type { ZohoMilestone } from '../types/task'
import { fetchMilestones } from '../api/client'

export function useProjectMilestones(projectId: string | null) {
  const [milestones, setMilestones] = useState<ZohoMilestone[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) { setMilestones([]); return }
    let cancelled = false
    setLoading(true)
    fetchMilestones(projectId)
      .then((data) => { if (!cancelled) setMilestones(data) })
      .catch(() => { if (!cancelled) setMilestones([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [projectId])

  return { milestones, loading }
}
```

- [ ] **Step 4: Write src/utils/validation.ts**

```typescript
import type { Task } from '../types/task'

export interface ValidationError {
  row_id: string
  fields: string[]
}

export function validateTasksForPush(tasks: Task[]): ValidationError[] {
  // Returns one entry per invalid task; empty array means all tasks are valid.
  return tasks.flatMap((task) => {
    const fields: string[] = []
    if (!task.task_name.trim()) fields.push('task_name')
    if (!task.description.trim()) fields.push('description')
    const hours = task.estimated_hours
    if (!hours || isNaN(hours) || hours < 0.5 || hours > 999) fields.push('estimated_hours')
    if (!task.billing_type) fields.push('billing_type')
    if (task.start_date && task.end_date && task.end_date < task.start_date) {
      fields.push('end_date')
    }
    return fields.length > 0 ? [{ row_id: task.row_id, fields }] : []
  })
}

export function isPushReady(tasks: Task[]): boolean {
  if (tasks.length === 0) return false  // check length first: no tasks → not ready
  return validateTasksForPush(tasks).length === 0
}
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add src/hooks/ src/utils/validation.ts
git commit -m "feat: add data-fetching hooks and push validation utility"
```

---

## Chunk 8: Frontend Components

### Task 13: ProjectSelector and InputPanel

**Files:**
- Create: `frontend/src/components/ProjectSelector.tsx`
- Create: `frontend/src/components/InputPanel.tsx`

- [ ] **Step 1: Write ProjectSelector.tsx**

```tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select'
import { useZohoProjects } from '../hooks/useZohoProjects'

interface Props {
  value: string | null
  onChange: (projectId: string) => void
}

export function ProjectSelector({ value, onChange }: Props) {
  const { projects, loading, error } = useZohoProjects()

  if (error) {
    return <p className="text-sm text-red-500">Failed to load Zoho projects: {error}</p>
  }

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-slate-700">Zoho Project</label>
      <Select value={value ?? ''} onValueChange={onChange} disabled={loading}>
        <SelectTrigger className="w-64">
          <SelectValue placeholder={loading ? 'Loading projects…' : projects.length === 0 ? 'No projects found' : 'Select a project'} />
        </SelectTrigger>
        <SelectContent>
          {projects.map((p) => (
            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
```

- [ ] **Step 2: Write InputPanel.tsx**

```tsx
import { useState } from 'react'
import { Button } from './ui/button'
import { fetchGoogleDoc } from '../api/client'

const MAX_CHARS = 50_000

interface Props {
  onSowReady: (text: string) => void
  disabled: boolean
}

export function InputPanel({ onSowReady, disabled }: Props) {
  const [mode, setMode] = useState<'paste' | 'url'>('paste')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [urlError, setUrlError] = useState<string | null>(null)
  const [fetchingUrl, setFetchingUrl] = useState(false)

  const charCount = text.length
  const overLimit = charCount > MAX_CHARS

  async function handleFetchUrl() {
    setUrlError(null)
    setFetchingUrl(true)
    try {
      const fetched = await fetchGoogleDoc(url)
      setText(fetched)
      setMode('paste')
      onSowReady(fetched)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to fetch document'
      setUrlError(message)
    } finally {
      setFetchingUrl(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        {(['paste', 'url'] as const).map((m) => (
          <button
            key={m}
            className={`text-sm px-3 py-1 rounded ${mode === m ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-700'}`}
            onClick={() => setMode(m)}
            disabled={disabled}
          >
            {m === 'paste' ? 'Paste Text' : 'Google Doc URL'}
          </button>
        ))}
      </div>

      {mode === 'paste' && (
        <div className="flex flex-col gap-1">
          <textarea
            className={`w-full h-48 p-2 border rounded text-sm font-mono resize-y ${overLimit ? 'border-red-500' : 'border-slate-300'}`}
            placeholder="Paste your SOW / WBS content here…"
            value={text}
            onChange={(e) => { setText(e.target.value); onSowReady(e.target.value) }}
            disabled={disabled}
          />
          <span className={`text-xs ${overLimit ? 'text-red-500 font-semibold' : 'text-slate-400'}`}>
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
            {overLimit && ' — over limit, please shorten'}
          </span>
        </div>
      )}

      {mode === 'url' && (
        <div className="flex flex-col gap-1">
          <div className="flex gap-2">
            <input
              className="flex-1 border border-slate-300 rounded px-2 py-1.5 text-sm"
              placeholder="https://docs.google.com/document/d/…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={fetchingUrl || disabled}
            />
            <Button size="sm" onClick={handleFetchUrl} disabled={!url.trim() || fetchingUrl || disabled}>
              {fetchingUrl ? 'Fetching…' : 'Fetch'}
            </Button>
          </div>
          {urlError && <p className="text-xs text-red-500">{urlError}</p>}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add src/components/ProjectSelector.tsx src/components/InputPanel.tsx
git commit -m "feat: add ProjectSelector and InputPanel components"
```

---

### Task 14: TaskTable component

**Files:**
- Create: `frontend/src/components/TaskTable.tsx`

The `onChange` prop signature is `(tasks: Task[]) => void` — receives the full updated task array. Each update creates a new array with the modified row, preserving all other rows. This is the contract `App.tsx` depends on.

- [ ] **Step 1: Write TaskTable.tsx**

```tsx
import { v4 as uuidv4 } from 'uuid'
import type { Task, BillingType, Priority, ZohoMember, ZohoMilestone } from '../types/task'
import { validateTasksForPush } from '../utils/validation'

interface Props {
  tasks: Task[]
  members: ZohoMember[]
  milestones: ZohoMilestone[]
  onChange: (tasks: Task[]) => void  // receives full updated task array
}

const BILLING_OPTIONS: BillingType[] = ['billable', 'non-billable']
const PRIORITY_OPTIONS: Priority[] = ['high', 'medium', 'low']

function emptyTask(): Task {
  return {
    row_id: uuidv4(),
    task_name: '',
    description: '',
    assignee_name: null,
    estimated_hours: 1.0,
    billing_type: 'billable',
    sprint_milestone: null,
    priority: null,
    dependencies: [],
    start_date: null,
    end_date: null,
  }
}

export function TaskTable({ tasks, members, milestones, onChange }: Props) {
  const errors = validateTasksForPush(tasks)
  const errorMap = Object.fromEntries(errors.map((e) => [e.row_id, new Set(e.fields)]))

  function update(row_id: string, patch: Partial<Task>) {
    onChange(tasks.map((t) => (t.row_id === row_id ? { ...t, ...patch } : t)))
  }

  function addRow() { onChange([...tasks, emptyTask()]) }
  function deleteRow(row_id: string) { onChange(tasks.filter((t) => t.row_id !== row_id)) }

  function cellClass(row_id: string, field: string, extra = '') {
    const hasError = errorMap[row_id]?.has(field)
    return `border rounded px-1 py-0.5 text-xs w-full ${hasError ? 'border-red-500 bg-red-50' : 'border-slate-200'} ${extra}`
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No tasks yet. Extract tasks from your SOW or add one manually.
        <div className="mt-2">
          <button onClick={addRow} className="text-blue-600 underline text-xs">+ Add task</button>
        </div>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-slate-100 text-slate-600 text-left">
            {['Task Name *', 'Description *', 'Assignee', 'Hours *', 'Billing *',
              'Milestone', 'Priority', 'Dependencies', 'Start Date', 'End Date', ''].map((h) => (
              <th key={h} className="p-2 border border-slate-200 min-w-[80px]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.row_id} className="hover:bg-slate-50">
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'task_name')} value={task.task_name}
                  onChange={(e) => update(task.row_id, { task_name: e.target.value })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'description')} value={task.description}
                  onChange={(e) => update(task.row_id, { description: e.target.value })} />
              </td>
              <td className="p-1 border border-slate-200">
                <select className={cellClass(task.row_id, 'assignee_name')}
                  value={task.assignee_name ?? ''}
                  onChange={(e) => update(task.row_id, { assignee_name: e.target.value || null })}>
                  <option value="">— unassigned —</option>
                  {members.map((m) => <option key={m.id} value={m.name}>{m.name}</option>)}
                </select>
              </td>
              <td className="p-1 border border-slate-200">
                <input type="number" step="0.5" min="0.5" max="999"
                  className={cellClass(task.row_id, 'estimated_hours', task._hours_defaulted ? 'bg-amber-50' : '')}
                  value={task.estimated_hours}
                  title={task._hours_defaulted ? 'Defaulted to 1.0 by AI — please verify' : undefined}
                  onChange={(e) => update(task.row_id, {
                    estimated_hours: parseFloat(e.target.value),
                    _hours_defaulted: false,
                  })} />
              </td>
              <td className="p-1 border border-slate-200">
                <select className={cellClass(task.row_id, 'billing_type')}
                  value={task.billing_type}
                  onChange={(e) => update(task.row_id, { billing_type: e.target.value as BillingType })}>
                  {BILLING_OPTIONS.map((b) => <option key={b} value={b}>{b}</option>)}
                </select>
              </td>
              <td className="p-1 border border-slate-200">
                {/* datalist provides autocomplete from fetched milestones */}
                <input list={`ms-${task.row_id}`}
                  className={cellClass(task.row_id, 'sprint_milestone')}
                  value={task.sprint_milestone ?? ''}
                  placeholder="optional"
                  onChange={(e) => update(task.row_id, { sprint_milestone: e.target.value || null })} />
                <datalist id={`ms-${task.row_id}`}>
                  {milestones.map((m) => <option key={m.id} value={m.name} />)}
                </datalist>
              </td>
              <td className="p-1 border border-slate-200">
                <select className={cellClass(task.row_id, 'priority')}
                  value={task.priority ?? ''}
                  onChange={(e) => update(task.row_id, { priority: (e.target.value as Priority) || null })}>
                  <option value="">—</option>
                  {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </td>
              <td className="p-1 border border-slate-200">
                <input className={cellClass(task.row_id, 'dependencies')}
                  value={task.dependencies.join(', ')}
                  placeholder="Task A, Task B"
                  onChange={(e) => update(task.row_id, {
                    dependencies: e.target.value
                      ? e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
                      : [],
                  })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input type="date" className={cellClass(task.row_id, 'start_date')}
                  value={task.start_date ?? ''}
                  onChange={(e) => update(task.row_id, { start_date: e.target.value || null })} />
              </td>
              <td className="p-1 border border-slate-200">
                <input type="date" className={cellClass(task.row_id, 'end_date')}
                  value={task.end_date ?? ''}
                  min={task.start_date ?? undefined}
                  onChange={(e) => update(task.row_id, { end_date: e.target.value || null })} />
              </td>
              <td className="p-1 border border-slate-200 text-center">
                <button onClick={() => deleteRow(task.row_id)}
                  className="text-red-400 hover:text-red-600 font-bold" title="Delete row">×</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={addRow} className="mt-2 text-blue-600 underline text-xs">+ Add task</button>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add src/components/TaskTable.tsx
git commit -m "feat: add editable TaskTable with validation highlights and milestone autocomplete"
```

---

### Task 15: FeedbackPanel component

**Files:**
- Create: `frontend/src/components/FeedbackPanel.tsx`

- [ ] **Step 1: Write FeedbackPanel.tsx**

```tsx
import type { PushTaskResult } from '../types/task'

interface Props {
  results: PushTaskResult[]
}

const STATUS_STYLES: Record<string, string> = {
  created: 'bg-green-100 text-green-800',
  warning: 'bg-amber-100 text-amber-800',
  failed:  'bg-red-100 text-red-800',
}

export function FeedbackPanel({ results }: Props) {
  if (results.length === 0) return null

  const counts = results.reduce(
    (acc, r) => ({ ...acc, [r.status]: (acc[r.status] ?? 0) + 1 }),
    {} as Record<string, number>
  )

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3 text-sm font-medium">
        {counts.created ? <span className="text-green-700">{counts.created} created</span> : null}
        {counts.warning ? <span className="text-amber-700">{counts.warning} with warnings</span> : null}
        {counts.failed  ? <span className="text-red-700">{counts.failed} failed</span> : null}
      </div>
      <div className="flex flex-col gap-2">
        {results.map((result) => (
          <div key={result.row_id}
            className="flex flex-col gap-1 p-2 rounded border border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_STYLES[result.status]}`}>
                {result.status}
              </span>
              <span className="text-sm font-medium text-slate-800">{result.task_name}</span>
              {result.zoho_task_id && (
                <span className="text-xs text-slate-400">#{result.zoho_task_id}</span>
              )}
            </div>
            {result.warnings.map((w, i) => (
              <p key={i} className="text-xs text-amber-700 ml-1" role="alert">Warning: {w}</p>
            ))}
            {result.error && (
              <p className="text-xs text-red-600 ml-1" role="alert">Error: {result.error}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/components/FeedbackPanel.tsx
git commit -m "feat: add FeedbackPanel for push results"
```

---

## Chunk 9: App Integration

### Task 16: App.tsx — wire everything together

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Write App.tsx**

Note: `_hours_defaulted` is set to `true` only when `estimated_hours === HOURS_SENTINEL` (imported constant `1.0`). This avoids float precision issues — the backend always returns exactly `1.0` (Python float literal) when using the sentinel, which JSON serializes to `1.0` and JavaScript parses as the number `1`. The `=== 1` check covers both representations.

```tsx
import { useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { ProjectSelector } from './components/ProjectSelector'
import { InputPanel } from './components/InputPanel'
import { TaskTable } from './components/TaskTable'
import { FeedbackPanel } from './components/FeedbackPanel'
import { Button } from './components/ui/button'
import { useProjectMembers } from './hooks/useProjectMembers'
import { useProjectMilestones } from './hooks/useProjectMilestones'
import { extractTasks, pushTasks } from './api/client'
import { isPushReady } from './utils/validation'
import { HOURS_SENTINEL } from './types/task'
import type { Task, PushTaskResult } from './types/task'

export default function App() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [sowText, setSowText] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState<string | null>(null)
  const [pushing, setPushing] = useState(false)
  const [pushResults, setPushResults] = useState<PushTaskResult[]>([])

  const { members, loading: membersLoading } = useProjectMembers(selectedProject)
  const { milestones } = useProjectMilestones(selectedProject)

  function handleProjectChange(projectId: string) {
    setSelectedProject(projectId)
    setTasks([])
    setPushResults([])
    setExtractError(null)
  }

  async function handleExtract() {
    if (!sowText.trim() || !selectedProject) return
    setExtracting(true)
    setExtractError(null)
    setPushResults([])
    try {
      const rawTasks = await extractTasks({
        sow_text: sowText,
        team_members: members.map((m) => m.name),
      })
      const tasksWithIds: Task[] = rawTasks.map((t) => ({
        ...t,
        row_id: uuidv4(),
        dependencies: t.dependencies ?? [],
        // Mark hours as defaulted when AI returned the sentinel value (1 or 1.0)
        _hours_defaulted: t.estimated_hours === HOURS_SENTINEL,
      }))
      setTasks(tasksWithIds)
    } catch (e: unknown) {
      const err = e as { body?: { error?: string; raw_response?: string }; message?: string }
      if (err.body?.error === 'parse_failed') {
        setExtractError(`AI could not parse the SOW. Raw response: ${err.body.raw_response}`)
      } else {
        setExtractError(err.message ?? 'Extraction failed')
      }
    } finally {
      setExtracting(false)
    }
  }

  async function handlePush() {
    if (!selectedProject || !isPushReady(tasks)) return
    setPushing(true)
    setPushResults([])
    try {
      const response = await pushTasks({ project_id: selectedProject, tasks })
      setPushResults(response.results)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Push failed'
      setPushResults([{
        row_id: 'global-error',
        task_name: 'All tasks',
        status: 'failed',
        zoho_task_id: null,
        warnings: [],
        error: message,
      }])
    } finally {
      setPushing(false)
    }
  }

  const canExtract = !!selectedProject && sowText.trim().length > 0 && sowText.length <= 50_000 && !extracting
  const canPush = isPushReady(tasks) && !pushing && !extracting

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <h1 className="text-xl font-bold text-slate-800">SOW Task Generator</h1>
        <p className="text-sm text-slate-500">
          Extract tasks from your SOW and push them directly to Zoho Projects
        </p>
      </header>

      <main className="max-w-screen-2xl mx-auto px-6 py-6 flex flex-col gap-6">
        <section className="bg-white rounded-lg border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
            1. Select Zoho Project
          </h2>
          <ProjectSelector value={selectedProject} onChange={handleProjectChange} />
        </section>

        <section className="bg-white rounded-lg border border-slate-200 p-5">
          <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
            2. Provide SOW / WBS
          </h2>
          <InputPanel onSowReady={setSowText} disabled={!selectedProject} />
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={handleExtract} disabled={!canExtract}>
              {extracting ? 'Extracting…' : 'Extract Tasks'}
            </Button>
            {membersLoading && (
              <span className="text-xs text-slate-400">Loading team members…</span>
            )}
          </div>
          {extractError && <p className="mt-2 text-sm text-red-600">{extractError}</p>}
        </section>

        {tasks.length > 0 && (
          <section className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
              3. Review & Edit Tasks ({tasks.length})
            </h2>
            <TaskTable tasks={tasks} members={members} milestones={milestones} onChange={setTasks} />
            <div className="mt-4">
              <Button onClick={handlePush} disabled={!canPush}>
                {pushing
                  ? 'Pushing to Zoho…'
                  : `Push ${tasks.length} Task${tasks.length !== 1 ? 's' : ''} to Zoho`}
              </Button>
              {!canPush && tasks.length > 0 && (
                <p className="mt-1 text-xs text-slate-400">Fix highlighted fields before pushing.</p>
              )}
            </div>
          </section>
        )}

        {pushResults.length > 0 && (
          <section className="bg-white rounded-lg border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-3">
              4. Push Results
            </h2>
            <FeedbackPanel results={pushResults} />
          </section>
        )}
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Update main.tsx**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Start both servers**

Terminal 1:
```bash
cd /c/Users/aesha/projects/sow-task-generator/backend
source .venv/Scripts/activate
uvicorn main:app --reload
```

Terminal 2:
```bash
cd /c/Users/aesha/projects/sow-task-generator/frontend
npm run dev
```

- [ ] **Step 5: Smoke test — verify backend endpoints respond**

```bash
curl -s http://localhost:8000/zoho/projects
```

Expected: JSON response (may be 503 if Zoho credentials not set — that's correct behavior, not a code error).

```bash
curl -s http://localhost:8000/docs
```

Expected: FastAPI OpenAPI UI HTML.

- [ ] **Step 6: Smoke test — verify frontend loads**

Open `http://localhost:5173` in browser.

Expected:
- Page renders with header "SOW Task Generator"
- Project dropdown is visible (may show "Failed to load Zoho projects" if no credentials — that's correct)
- No console errors about missing modules or type errors

- [ ] **Step 7: Run final backend test suite**

```bash
cd /c/Users/aesha/projects/sow-task-generator/backend
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
cd /c/Users/aesha/projects/sow-task-generator
git add frontend/src/App.tsx frontend/src/main.tsx
git commit -m "feat: wire up App with full extract → review → push flow"
```

- [ ] **Step 9: Final commit for all remaining files**

```bash
git status
git add -A
git commit -m "chore: finalize project setup — env templates, gitignore, docs"
```
