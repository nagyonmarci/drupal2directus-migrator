"""Read Drupal 10 managed files from the database."""
from src.drupal import db
from src import config
from src.logger import get_logger

logger = get_logger(__name__)

_PUBLIC_SCHEME = "public://"
_FILES_PATH = "/sites/default/files/"


def get_managed_files(status: int = 1) -> list[dict]:
    """Return all active managed files."""
    rows = db.fetchall(
        "SELECT fid, uuid, filename, uri, filemime, filesize, status FROM file_managed WHERE status = %s ORDER BY fid",
        (status,),
    )
    logger.debug(f"Found {len(rows)} managed files.")
    return rows


def uri_to_url(uri: str) -> str:
    """Convert a Drupal public:// URI to a full download URL."""
    if uri.startswith(_PUBLIC_SCHEME):
        relative = uri[len(_PUBLIC_SCHEME):]
        return f"{config.DRUPAL_BASE_URL}{_FILES_PATH}{relative}"
    # private:// or other schemes — not downloadable without special handling
    logger.warning(f"Non-public URI, skipping: {uri}")
    return ""


def get_file_count() -> int:
    row = db.fetchone("SELECT COUNT(*) AS cnt FROM file_managed WHERE status=1")
    return row["cnt"] if row else 0
