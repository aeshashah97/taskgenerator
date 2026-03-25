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

    # --- New assignee_names validator tests ---

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
