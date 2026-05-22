from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, SecretStr, field_serializer


class ConnectionCreate(BaseModel):
    name: str
    drupal_base_url: str
    drupal_db_host: str
    drupal_db_port: int = 3306
    drupal_db_name: str
    drupal_db_user: str
    drupal_db_password: SecretStr
    drupal_api_user: str
    drupal_api_password: SecretStr
    directus_url: str
    directus_admin_token: SecretStr


class Connection(BaseModel):
    id: str
    name: str
    drupal_base_url: str
    drupal_db_host: str
    drupal_db_port: int
    drupal_db_name: str
    drupal_db_user: str
    drupal_db_password: SecretStr
    drupal_api_user: str
    drupal_api_password: SecretStr
    directus_url: str
    directus_admin_token: SecretStr
    created_at: datetime

    @field_serializer("drupal_db_password", "drupal_api_password", "directus_admin_token")
    def mask_secret(self, v: SecretStr) -> str:
        return "**masked**"

    def to_env_dict(self) -> dict[str, str]:
        return {
            "DRUPAL_DB_HOST": self.drupal_db_host,
            "DRUPAL_DB_PORT": str(self.drupal_db_port),
            "DRUPAL_DB_NAME": self.drupal_db_name,
            "DRUPAL_DB_USER": self.drupal_db_user,
            "DRUPAL_DB_PASSWORD": self.drupal_db_password.get_secret_value(),
            "DRUPAL_BASE_URL": self.drupal_base_url.rstrip("/"),
            "DRUPAL_API_USER": self.drupal_api_user,
            "DRUPAL_API_PASSWORD": self.drupal_api_password.get_secret_value(),
            "DIRECTUS_URL": self.directus_url.rstrip("/"),
            "DIRECTUS_ADMIN_TOKEN": self.directus_admin_token.get_secret_value(),
        }


class ConnectionPublic(BaseModel):
    """Connection without secrets, safe to return in API responses."""
    id: str
    name: str
    drupal_base_url: str
    drupal_db_host: str
    drupal_db_port: int
    drupal_db_name: str
    drupal_db_user: str
    drupal_api_user: str
    directus_url: str
    created_at: datetime


class TestResult(BaseModel):
    drupal_db: bool
    drupal_api: bool
    directus: bool
    errors: list[str]

    @property
    def ok(self) -> bool:
        return self.drupal_db and self.drupal_api and self.directus


class JobCreate(BaseModel):
    connection_id: str
    phases: list[int]
    label: Optional[str] = None


class Job(BaseModel):
    id: str
    connection_id: str
    connection_name: str
    phases: list[int]
    label: str
    status: Literal["pending", "running", "done", "failed", "cancelled"]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_phase: Optional[int] = None
    error: Optional[str] = None
    log_path: str
