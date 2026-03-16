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
