import time
from typing import Any

import httpx

from src import config
from src.logger import get_logger

logger = get_logger(__name__)

_TIMEOUT = httpx.Timeout(60.0)
_MAX_RETRIES = 4
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class DirectusClient:
    def __init__(self) -> None:
        self._base = config.DIRECTUS_URL
        self._headers = {
            "Authorization": f"Bearer {config.DIRECTUS_ADMIN_TOKEN}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(timeout=_TIMEOUT)
        self._validate_token()

    def _validate_token(self) -> None:
        resp = self._client.get(f"{self._base}/server/info", headers=self._headers)
        if resp.status_code != 200:
            raise PermissionError(
                f"DIRECTUS_ADMIN_TOKEN is invalid or expired (HTTP {resp.status_code}). "
                "Check your .env file."
            )
        logger.debug("Directus admin token validated.")

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self._base}{path}"
        headers = {**self._headers, **kwargs.pop("extra_headers", {})}
        for attempt in range(_MAX_RETRIES):
            resp = self._client.request(method, url, headers=headers, **kwargs)
            if resp.status_code not in _RETRY_STATUSES:
                return resp
            wait = 2 ** attempt
            logger.warning(f"HTTP {resp.status_code} on {method} {path}; retrying in {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
        return resp

    def get(self, path: str, params: dict | None = None) -> Any:
        resp = self._request("GET", path, params=params)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, data: dict | None = None) -> Any:
        resp = self._request("POST", path, json=data)
        resp.raise_for_status()
        return resp.json()

    def patch(self, path: str, data: dict | None = None) -> Any:
        resp = self._request("PATCH", path, json=data)
        resp.raise_for_status()
        return resp.json()

    def delete(self, path: str) -> None:
        resp = self._request("DELETE", path)
        resp.raise_for_status()

    def upload_file(self, filename: str, content: bytes, mime_type: str, extra_data: dict | None = None) -> dict:
        files = {"file": (filename, content, mime_type)}
        data = extra_data or {}
        headers = {"Authorization": f"Bearer {config.DIRECTUS_ADMIN_TOKEN}"}
        resp = self._request("POST", "/files", files=files, data=data, extra_headers=headers)
        resp.raise_for_status()
        return resp.json()

    def apply_schema(self, diff: dict) -> dict:
        """Apply a schema diff via PATCH /schema/apply (idempotent)."""
        resp = self._request("POST", "/schema/diff", json=diff)
        if resp.status_code == 204:
            logger.debug("Schema already up-to-date, no changes applied.")
            return {}
        resp.raise_for_status()
        schema_diff = resp.json()
        apply_resp = self._request("POST", "/schema/apply", json=schema_diff)
        apply_resp.raise_for_status()
        return apply_resp.json()

    def server_info(self) -> dict:
        return self.get("/server/info")

    def close(self) -> None:
        self._client.close()
