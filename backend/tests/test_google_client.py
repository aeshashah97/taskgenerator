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
