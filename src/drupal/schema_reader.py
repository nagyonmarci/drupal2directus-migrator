"""Read Drupal 10 content types, fields, and taxonomies from the database."""
from src.drupal import db
from src.logger import get_logger

logger = get_logger(__name__)

DRUPAL_TO_DIRECTUS_TYPE: dict[str, str] = {
    "string": "string",
    "string_long": "text",
    "list_string": "string",
    "text": "text",
    "text_long": "text",
    "text_with_summary": "text",
    "integer": "integer",
    "float": "float",
    "decimal": "decimal",
    "boolean": "boolean",
    "datetime": "dateTime",
    "timestamp": "dateTime",
    "image": "uuid",
    "file": "uuid",
    "link": "json",
    "email": "string",
    "telephone": "string",
    "geofield": "json",
    "address": "json",
    "entity_reference": "integer",
}


def get_content_types() -> list[dict]:
    """Return all Drupal node content types."""
    rows = db.fetchall(
        "SELECT type, name, description FROM node_type ORDER BY type"
    )
    logger.debug(f"Found {len(rows)} content types.")
    return rows


def get_fields_for_type(content_type: str) -> list[dict]:
    """Return field definitions for a given content type."""
    rows = db.fetchall(
        """
        SELECT
            fc.field_name,
            fc.bundle,
            fc.label,
            fc.required,
            fsc.type AS field_type,
            fsc.cardinality,
            fc.settings
        FROM field_config fc
        JOIN field_storage_config fsc
          ON fc.field_name = fsc.field_name
        WHERE fc.bundle = %s
          AND fc.entity_type = 'node'
          AND fc.deleted = 0
        ORDER BY fc.field_name
        """,
        (content_type,),
    )
    return rows


def get_all_fields() -> dict[str, list[dict]]:
    """Return a mapping of content_type -> list of field defs."""
    content_types = get_content_types()
    result: dict[str, list[dict]] = {}
    for ct in content_types:
        machine_name = ct["type"]
        result[machine_name] = get_fields_for_type(machine_name)
    return result


def get_taxonomies() -> list[dict]:
    """Return all taxonomy vocabularies."""
    rows = db.fetchall(
        "SELECT vid, name, description FROM taxonomy_vocabulary ORDER BY vid"
    )
    logger.debug(f"Found {len(rows)} taxonomy vocabularies.")
    return rows


def get_entity_reference_target(content_type: str, field_name: str) -> str | None:
    """
    Determine what entity type an entity_reference field points to.
    Returns 'taxonomy_term', 'node', or None.
    """
    row = db.fetchone(
        """
        SELECT settings FROM field_storage_config
        WHERE field_name = %s AND entity_type = 'node'
        """,
        (field_name,),
    )
    if not row:
        return None
    import json
    settings = json.loads(row["settings"]) if isinstance(row["settings"], str) else row.get("settings", {})
    return settings.get("target_type")


def map_field_type(drupal_type: str) -> str:
    return DRUPAL_TO_DIRECTUS_TYPE.get(drupal_type, "string")
