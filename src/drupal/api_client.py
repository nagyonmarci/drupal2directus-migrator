import httpx
from typing import Any

from src import config
from src.logger import get_logger

logger = get_logger(__name__)

_TIMEOUT = httpx.Timeout(30.0)
_JSONAPI_PREFIX = "/jsonapi"


class DrupalApiClient:
    def __init__(self) -> None:
        self._base = config.DRUPAL_BASE_URL
        self._session_headers: dict[str, str] = {}
        self._client = httpx.Client(timeout=_TIMEOUT)
        self._authenticate()

    def _authenticate(self) -> None:
        resp = self._client.post(
            f"{self._base}/user/login?_format=json",
            json={"name": config.DRUPAL_API_USER, "pass": config.DRUPAL_API_PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("csrf_token", "")
        self._session_headers = {
            "X-CSRF-Token": token,
            "Cookie": "; ".join(f"{k}={v}" for k, v in self._client.cookies.items()),
        }
        logger.debug("Drupal REST API authentication successful.")

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._client.get(url, headers=self._session_headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def list_nodes(self, node_type: str, offset: int = 0, limit: int = 50) -> dict:
        url = f"{self._base}{_JSONAPI_PREFIX}/node/{node_type}"
        params = {
            "page[offset]": offset,
            "page[limit]": limit,
            "sort": "nid",
        }
        return self._get(url, params)

    def get_node(self, node_type: str, uuid: str) -> dict:
        url = f"{self._base}{_JSONAPI_PREFIX}/node/{node_type}/{uuid}"
        return self._get(url)

    def list_taxonomy_terms(self, vocabulary: str, offset: int = 0, limit: int = 50) -> dict:
        url = f"{self._base}{_JSONAPI_PREFIX}/taxonomy_term/{vocabulary}"
        params = {"page[offset]": offset, "page[limit]": limit}
        return self._get(url, params)

    def ping(self) -> bool:
        try:
            resp = self._client.get(f"{self._base}{_JSONAPI_PREFIX}", timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        self._client.close()
