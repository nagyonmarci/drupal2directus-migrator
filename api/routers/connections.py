from __future__ import annotations

import httpx
import mysql.connector
from fastapi import APIRouter, HTTPException, status

from api.models import ConnectionCreate, ConnectionPublic, TestResult
from api import store

router = APIRouter(prefix="/api/connections", tags=["connections"])


def _public(conn) -> ConnectionPublic:
    return ConnectionPublic(
        id=conn.id,
        name=conn.name,
        drupal_base_url=conn.drupal_base_url,
        drupal_db_host=conn.drupal_db_host,
        drupal_db_port=conn.drupal_db_port,
        drupal_db_name=conn.drupal_db_name,
        drupal_db_user=conn.drupal_db_user,
        drupal_api_user=conn.drupal_api_user,
        directus_url=conn.directus_url,
        created_at=conn.created_at,
    )


@router.get("", response_model=list[ConnectionPublic])
def list_connections():
    return [_public(c) for c in store.list_connections()]


@router.post("", response_model=ConnectionPublic, status_code=status.HTTP_201_CREATED)
def create_connection(payload: ConnectionCreate):
    conn = store.create_connection(payload)
    return _public(conn)


@router.delete("/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(conn_id: str):
    if not store.delete_connection(conn_id):
        raise HTTPException(status_code=404, detail="Connection not found")


@router.post("/{conn_id}/test", response_model=TestResult)
def test_connection(conn_id: str):
    conn = store.get_connection(conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    errors: list[str] = []
    db_ok = False
    api_ok = False
    directus_ok = False

    # Test Drupal MySQL
    try:
        db = mysql.connector.connect(
            host=conn.drupal_db_host,
            port=conn.drupal_db_port,
            database=conn.drupal_db_name,
            user=conn.drupal_db_user,
            password=conn.drupal_db_password.get_secret_value(),
            connect_timeout=5,
        )
        db.close()
        db_ok = True
    except Exception as e:
        errors.append(f"Drupal DB: {e}")

    # Test Drupal REST API
    try:
        resp = httpx.get(
            f"{conn.drupal_base_url.rstrip('/')}/jsonapi",
            timeout=8,
        )
        api_ok = resp.status_code == 200
        if not api_ok:
            errors.append(f"Drupal API: HTTP {resp.status_code}")
    except Exception as e:
        errors.append(f"Drupal API: {e}")

    # Test Directus
    try:
        resp = httpx.get(
            f"{conn.directus_url.rstrip('/')}/server/info",
            headers={"Authorization": f"Bearer {conn.directus_admin_token.get_secret_value()}"},
            timeout=8,
        )
        directus_ok = resp.status_code == 200
        if not directus_ok:
            errors.append(f"Directus: HTTP {resp.status_code} — invalid token?")
    except Exception as e:
        errors.append(f"Directus: {e}")

    return TestResult(drupal_db=db_ok, drupal_api=api_ok, directus=directus_ok, errors=errors)
