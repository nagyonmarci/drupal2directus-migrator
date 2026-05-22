from contextlib import contextmanager
from typing import Any, Generator

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

from src import config
from src.logger import get_logger

logger = get_logger(__name__)

_pool: MySQLConnectionPool | None = None


def _get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name="drupal_pool",
            pool_size=5,
            host=config.DRUPAL_DB_HOST,
            port=config.DRUPAL_DB_PORT,
            database=config.DRUPAL_DB_NAME,
            user=config.DRUPAL_DB_USER,
            password=config.DRUPAL_DB_PASSWORD,
            charset="utf8mb4",
            use_pure=True,
        )
        logger.debug("MySQL connection pool created.")
    return _pool


@contextmanager
def get_cursor(dictionary: bool = True) -> Generator:
    pool = _get_pool()
    conn = pool.get_connection()
    try:
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def fetchall(query: str, params: tuple = ()) -> list[dict]:
    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def fetchone(query: str, params: tuple = ()) -> dict | None:
    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()


def test_connection() -> dict:
    """Return basic DB stats to confirm connectivity."""
    row = fetchone("SELECT VERSION() AS version, DATABASE() AS db_name")
    return row or {}
