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

    def close(self) -> None:
        self._http.close()
