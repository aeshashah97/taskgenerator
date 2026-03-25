import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from routers.push_router import _resolve_assignees


# --- Unit tests for resolver helpers ---

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



# --- Integration tests for /push endpoint ---

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


@pytest.fixture
def zoho_mock():
    with patch("routers.push_router.ZohoClient") as MockZoho:
        instance = MagicMock()
        instance.get_members.return_value = [{"id": "user-1", "name": "Alice"}]
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
    task = make_push_task({"assignee_names": ["Unknown Person"]})
    response = test_client.post(
        "/push", json={"project_id": "proj-1", "tasks": [task]},
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "warning"
    assert any("assignee" in w.lower() for w in result["warnings"])


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
    assert any("source task failed to create" in w for w in result_b["warnings"])


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
