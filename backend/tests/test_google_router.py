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
