"""Read Drupal 10 Views and custom blocks from the database."""
import json
from src.drupal import db
from src.logger import get_logger

logger = get_logger(__name__)


def get_views() -> list[dict]:
    """Return all Drupal Views configurations from the config table."""
    rows = db.fetchall(
        "SELECT name, data FROM config WHERE name LIKE 'views.view.%' ORDER BY name"
    )
    parsed = []
    for row in rows:
        view_name = row["name"].replace("views.view.", "")
        raw = row["data"]
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        try:
            config_data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse config for view '{view_name}', skipping.")
            continue
        parsed.append({"machine_name": view_name, "config": config_data})
    logger.debug(f"Found {len(parsed)} views.")
    return parsed


def get_custom_blocks() -> list[dict]:
    """Return all custom block content."""
    rows = db.fetchall(
        """
        SELECT
            b.id,
            b.uuid,
            b.type,
            b.info AS machine_name,
            f.body_value AS body,
            f.body_format
        FROM block_content b
        LEFT JOIN block_content__body f ON b.id = f.entity_id AND f.deleted = 0
        ORDER BY b.id
        """
    )
    logger.debug(f"Found {len(rows)} custom blocks.")
    return rows


def get_block_region(block_uuid: str) -> str | None:
    """Attempt to find what region a block was placed in."""
    row = db.fetchone(
        "SELECT region FROM block WHERE uuid = %s LIMIT 1",
        (block_uuid,),
    )
    return row["region"] if row else None
