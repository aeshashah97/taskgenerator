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
