import pytest
from unittest.mock import MagicMock, patch
from clients.claude_client import ClaudeClient, HOURS_SENTINEL


class TestClaudeClientConstants:
    def test_hours_sentinel_is_one(self):
        assert HOURS_SENTINEL == 1.0


class TestClaudeClientExtract:
    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")
        return ClaudeClient()

    def test_extract_tasks_returns_task_list(self, client):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='[{"task_name": "Setup CI", "description": "Configure CI pipeline", "estimated_hours": 2.0, "billing_type": "billable"}]')]
        with patch.object(client._anthropic, "messages") as mock_messages:
            mock_messages.create.return_value = mock_message
            tasks = client.extract_tasks("Build a CI pipeline", [])
        assert isinstance(tasks, list)
        assert tasks[0]["task_name"] == "Setup CI"

    def test_extract_tasks_passes_sow_text_to_claude(self, client):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='[]')]
        with patch.object(client._anthropic, "messages") as mock_messages:
            mock_messages.create.return_value = mock_message
            client.extract_tasks("My SOW content here", ["Alice", "Bob"])
        call_kwargs = mock_messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]
        assert "My SOW content here" in user_content
        assert "Alice" in user_content
        assert "Bob" in user_content

    def test_extract_tasks_uses_correct_model(self, client):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='[]')]
        with patch.object(client._anthropic, "messages") as mock_messages:
            mock_messages.create.return_value = mock_message
            client.extract_tasks("SOW text", [])
        call_kwargs = mock_messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    def test_extract_tasks_raises_on_invalid_json(self, client):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='not valid json')]
        with patch.object(client._anthropic, "messages") as mock_messages:
            mock_messages.create.return_value = mock_message
            with pytest.raises(ValueError, match="parse_failed"):
                client.extract_tasks("SOW text", [])

    def test_extract_tasks_raises_on_non_list_json(self, client):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"key": "value"}')]
        with patch.object(client._anthropic, "messages") as mock_messages:
            mock_messages.create.return_value = mock_message
            with pytest.raises(ValueError, match="parse_failed"):
                client.extract_tasks("SOW text", [])

    def test_extract_tasks_raises_value_error_with_raw_response(self, client):
        raw = "this is bad output"
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=raw)]
        with patch.object(client._anthropic, "messages") as mock_messages:
            mock_messages.create.return_value = mock_message
            with pytest.raises(ValueError) as exc_info:
                client.extract_tasks("SOW text", [])
        assert raw in str(exc_info.value)
