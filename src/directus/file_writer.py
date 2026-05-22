"""Download files from Drupal and upload them to Directus."""
import httpx
from src.directus.client import DirectusClient
from src.logger import get_logger

logger = get_logger(__name__)

_DOWNLOAD_TIMEOUT = httpx.Timeout(120.0)


def download_file(url: str) -> tuple[bytes, str]:
    """Download a file from a URL. Returns (content_bytes, detected_mime)."""
    with httpx.Client(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "application/octet-stream").split(";")[0]
        return resp.content, mime


def upload_file(
    client: DirectusClient,
    filename: str,
    content: bytes,
    mime_type: str,
    title: str | None = None,
) -> str:
    """Upload file bytes to Directus and return the new file UUID."""
    extra: dict = {}
    if title:
        extra["title"] = title

    resp = client.upload_file(filename, content, mime_type, extra_data=extra or None)
    file_id: str = resp["data"]["id"]
    logger.info(f"Uploaded '{filename}' → Directus file {file_id}")
    return file_id
