import json
import os
import time
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
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    def _load_refresh_token(self) -> str:
        if Path(TOKEN_FILE).exists():
            data = json.loads(Path(TOKEN_FILE).read_text())
            return data.get("refresh_token", "")
        return os.getenv("ZOHO_REFRESH_TOKEN", "")

    def _save_refresh_token(self, token: str) -> None:
        Path(TOKEN_FILE).write_text(json.dumps({"refresh_token": token}))

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
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
            raise RuntimeError(f"Failed to refresh Zoho token: {data.get('error', 'unknown')}")
        self._access_token = access_token
        self._token_expires_at = time.time() + 3500  # expire 100s early to be safe
        new_refresh = data.get("refresh_token")
        if new_refresh:
            self._refresh_token = new_refresh
            self._save_refresh_token(new_refresh)
        return access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Zoho-oauthtoken {self._get_access_token()}"}

    def close(self) -> None:
        self._http.close()

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

    def create_task(self, project_id: str, payload: dict) -> dict:
        url = f"{ZOHO_BASE}/projects/{project_id}/tasks/"
        response = self._http.post(url, headers=self._headers(), data=payload)
        if not response.is_success:
            raise RuntimeError(f"Zoho {response.status_code}: {response.text}")
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
