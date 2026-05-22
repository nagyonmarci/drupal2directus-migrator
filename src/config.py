import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Required environment variable '{key}' is not set. Check your .env file.")
    return val


# ── Module-level globals (used by standalone scripts via .env) ────────────────

DRUPAL_DB_HOST: str = os.getenv("DRUPAL_DB_HOST", "")
DRUPAL_DB_PORT: int = int(os.getenv("DRUPAL_DB_PORT", "3306"))
DRUPAL_DB_NAME: str = os.getenv("DRUPAL_DB_NAME", "")
DRUPAL_DB_USER: str = os.getenv("DRUPAL_DB_USER", "")
DRUPAL_DB_PASSWORD: str = os.getenv("DRUPAL_DB_PASSWORD", "")

DRUPAL_BASE_URL: str = os.getenv("DRUPAL_BASE_URL", "").rstrip("/")
DRUPAL_API_USER: str = os.getenv("DRUPAL_API_USER", "")
DRUPAL_API_PASSWORD: str = os.getenv("DRUPAL_API_PASSWORD", "")

DIRECTUS_URL: str = os.getenv("DIRECTUS_URL", "").rstrip("/")
DIRECTUS_ADMIN_TOKEN: str = os.getenv("DIRECTUS_ADMIN_TOKEN", "")

BATCH_SIZE_FILES: int = int(os.getenv("BATCH_SIZE_FILES", "50"))
BATCH_SIZE_CONTENT: int = int(os.getenv("BATCH_SIZE_CONTENT", "100"))

STATE_FILE: str = os.getenv("STATE_FILE", "migration_state.json")


# ── Per-job Config object (used by the API) ───────────────────────────────────

@dataclass
class Config:
    drupal_db_host: str
    drupal_db_name: str
    drupal_db_user: str
    drupal_db_password: str
    drupal_base_url: str
    drupal_api_user: str
    drupal_api_password: str
    directus_url: str
    directus_admin_token: str
    drupal_db_port: int = 3306
    batch_size_files: int = 50
    batch_size_content: int = 100
    state_file: str = "migration_state.json"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            drupal_db_host=_require("DRUPAL_DB_HOST"),
            drupal_db_port=int(os.getenv("DRUPAL_DB_PORT", "3306")),
            drupal_db_name=_require("DRUPAL_DB_NAME"),
            drupal_db_user=_require("DRUPAL_DB_USER"),
            drupal_db_password=_require("DRUPAL_DB_PASSWORD"),
            drupal_base_url=_require("DRUPAL_BASE_URL").rstrip("/"),
            drupal_api_user=_require("DRUPAL_API_USER"),
            drupal_api_password=_require("DRUPAL_API_PASSWORD"),
            directus_url=_require("DIRECTUS_URL").rstrip("/"),
            directus_admin_token=_require("DIRECTUS_ADMIN_TOKEN"),
            batch_size_files=int(os.getenv("BATCH_SIZE_FILES", "50")),
            batch_size_content=int(os.getenv("BATCH_SIZE_CONTENT", "100")),
            state_file=os.getenv("STATE_FILE", "migration_state.json"),
        )

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        return cls(
            drupal_db_host=d["drupal_db_host"],
            drupal_db_port=int(d.get("drupal_db_port", 3306)),
            drupal_db_name=d["drupal_db_name"],
            drupal_db_user=d["drupal_db_user"],
            drupal_db_password=d["drupal_db_password"],
            drupal_base_url=d["drupal_base_url"].rstrip("/"),
            drupal_api_user=d["drupal_api_user"],
            drupal_api_password=d["drupal_api_password"],
            directus_url=d["directus_url"].rstrip("/"),
            directus_admin_token=d["directus_admin_token"],
            batch_size_files=int(d.get("batch_size_files", 50)),
            batch_size_content=int(d.get("batch_size_content", 100)),
            state_file=d.get("state_file", "migration_state.json"),
        )

    def to_env_dict(self) -> dict[str, str]:
        """Convert to env vars dict for subprocess injection."""
        return {
            "DRUPAL_DB_HOST": self.drupal_db_host,
            "DRUPAL_DB_PORT": str(self.drupal_db_port),
            "DRUPAL_DB_NAME": self.drupal_db_name,
            "DRUPAL_DB_USER": self.drupal_db_user,
            "DRUPAL_DB_PASSWORD": self.drupal_db_password,
            "DRUPAL_BASE_URL": self.drupal_base_url,
            "DRUPAL_API_USER": self.drupal_api_user,
            "DRUPAL_API_PASSWORD": self.drupal_api_password,
            "DIRECTUS_URL": self.directus_url,
            "DIRECTUS_ADMIN_TOKEN": self.directus_admin_token,
            "BATCH_SIZE_FILES": str(self.batch_size_files),
            "BATCH_SIZE_CONTENT": str(self.batch_size_content),
            "STATE_FILE": self.state_file,
        }
