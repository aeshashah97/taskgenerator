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
    mock_instance.extract_tasks.side_effect = ValueError("parse_failed: invalid json. raw_response: bad output")
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
