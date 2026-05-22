import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Required environment variable '{key}' is not set. Check your .env file.")
    return val


DRUPAL_DB_HOST: str = _require("DRUPAL_DB_HOST")
DRUPAL_DB_PORT: int = int(os.getenv("DRUPAL_DB_PORT", "3306"))
DRUPAL_DB_NAME: str = _require("DRUPAL_DB_NAME")
DRUPAL_DB_USER: str = _require("DRUPAL_DB_USER")
DRUPAL_DB_PASSWORD: str = _require("DRUPAL_DB_PASSWORD")

DRUPAL_BASE_URL: str = _require("DRUPAL_BASE_URL").rstrip("/")
DRUPAL_API_USER: str = _require("DRUPAL_API_USER")
DRUPAL_API_PASSWORD: str = _require("DRUPAL_API_PASSWORD")

DIRECTUS_URL: str = _require("DIRECTUS_URL").rstrip("/")
DIRECTUS_ADMIN_TOKEN: str = _require("DIRECTUS_ADMIN_TOKEN")

BATCH_SIZE_FILES: int = int(os.getenv("BATCH_SIZE_FILES", "50"))
BATCH_SIZE_CONTENT: int = int(os.getenv("BATCH_SIZE_CONTENT", "100"))

STATE_FILE: str = os.getenv("STATE_FILE", "migration_state.json")
