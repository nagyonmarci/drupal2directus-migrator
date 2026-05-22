"""File-based persistence for connections and jobs.

Secrets are stored encrypted-at-rest concern is left to the operator
(volume encryption / secrets manager). They are never logged or returned
in API responses (masked by the Pydantic serializer in models.py).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from api.models import Connection, ConnectionCreate, Job, JobCreate

_DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
_CONNECTIONS_FILE = _DATA_DIR / "connections.json"
_JOBS_FILE = _DATA_DIR / "jobs.json"

_conn_lock = threading.Lock()
_job_lock = threading.Lock()


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Connections ───────────────────────────────────────────────────────────────

def _load_connections_raw() -> list[dict]:
    if not _CONNECTIONS_FILE.exists():
        return []
    return json.loads(_CONNECTIONS_FILE.read_text())


def _save_connections_raw(data: list[dict]) -> None:
    _ensure_data_dir()
    _CONNECTIONS_FILE.write_text(json.dumps(data, indent=2, default=str))


def list_connections() -> list[Connection]:
    with _conn_lock:
        return [Connection(**c) for c in _load_connections_raw()]


def get_connection(conn_id: str) -> Optional[Connection]:
    with _conn_lock:
        for c in _load_connections_raw():
            if c["id"] == conn_id:
                return Connection(**c)
    return None


def create_connection(payload: ConnectionCreate) -> Connection:
    conn = Connection(
        id=str(uuid4()),
        name=payload.name,
        drupal_base_url=payload.drupal_base_url,
        drupal_db_host=payload.drupal_db_host,
        drupal_db_port=payload.drupal_db_port,
        drupal_db_name=payload.drupal_db_name,
        drupal_db_user=payload.drupal_db_user,
        drupal_db_password=payload.drupal_db_password,
        drupal_api_user=payload.drupal_api_user,
        drupal_api_password=payload.drupal_api_password,
        directus_url=payload.directus_url,
        directus_admin_token=payload.directus_admin_token,
        created_at=datetime.now(timezone.utc),
    )
    with _conn_lock:
        data = _load_connections_raw()
        # Store secrets as plain strings in the data file
        raw = conn.model_dump(mode="json")
        raw["drupal_db_password"] = payload.drupal_db_password.get_secret_value()
        raw["drupal_api_password"] = payload.drupal_api_password.get_secret_value()
        raw["directus_admin_token"] = payload.directus_admin_token.get_secret_value()
        data.append(raw)
        _save_connections_raw(data)
    return conn


def delete_connection(conn_id: str) -> bool:
    with _conn_lock:
        data = _load_connections_raw()
        new_data = [c for c in data if c["id"] != conn_id]
        if len(new_data) == len(data):
            return False
        _save_connections_raw(new_data)
    return True


# ── Jobs ──────────────────────────────────────────────────────────────────────

def _load_jobs_raw() -> list[dict]:
    if not _JOBS_FILE.exists():
        return []
    return json.loads(_JOBS_FILE.read_text())


def _save_jobs_raw(data: list[dict]) -> None:
    _ensure_data_dir()
    _JOBS_FILE.write_text(json.dumps(data, indent=2, default=str))


def list_jobs() -> list[Job]:
    with _job_lock:
        return [Job(**j) for j in _load_jobs_raw()]


def get_job(job_id: str) -> Optional[Job]:
    with _job_lock:
        for j in _load_jobs_raw():
            if j["id"] == job_id:
                return Job(**j)
    return None


def create_job(payload: JobCreate, connection_name: str) -> Job:
    _ensure_data_dir()
    job_id = str(uuid4())
    log_path = str(_DATA_DIR / "jobs" / job_id / "output.log")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    job = Job(
        id=job_id,
        connection_id=payload.connection_id,
        connection_name=connection_name,
        phases=sorted(set(payload.phases)),
        label=payload.label or f"Migration {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        status="pending",
        created_at=datetime.now(timezone.utc),
        log_path=log_path,
    )
    with _job_lock:
        data = _load_jobs_raw()
        data.append(job.model_dump(mode="json"))
        _save_jobs_raw(data)
    return job


def update_job(job_id: str, **kwargs) -> Optional[Job]:
    with _job_lock:
        data = _load_jobs_raw()
        for i, j in enumerate(data):
            if j["id"] == job_id:
                data[i].update(kwargs)
                _save_jobs_raw(data)
                return Job(**data[i])
    return None
