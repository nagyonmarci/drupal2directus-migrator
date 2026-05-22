"""Read Drupal nodes via REST API; read field values via DB for completeness."""
import re
from typing import Any

from src.drupal import db
from src.drupal.api_client import DrupalApiClient
from src.drupal.schema_reader import get_content_types, get_fields_for_type
from src.logger import get_logger

logger = get_logger(__name__)

# Patterns to strip from Drupal body HTML
_DRUPAL_TOKEN_RE = re.compile(r"\[(?:node|site|user|term|field|current-user):[^\]]+\]")
_DRUPAL_EMBED_RE = re.compile(r'<drupal-entity[^>]*>.*?</drupal-entity>', re.DOTALL)
_DRUPAL_MEDIA_RE = re.compile(r'<drupal-media[^>]*/?>', re.DOTALL)


def clean_html(html: str) -> str:
    """Remove Drupal-specific tokens and embed tags from body HTML."""
    html = _DRUPAL_TOKEN_RE.sub("", html)
    html = _DRUPAL_EMBED_RE.sub("", html)
    html = _DRUPAL_MEDIA_RE.sub("", html)
    return html.strip()


def get_taxonomy_terms(vocabulary: str) -> list[dict]:
    """Read taxonomy terms for a given vocabulary from DB."""
    return db.fetchall(
        """
        SELECT
            t.tid,
            t.vid,
            t.uuid,
            d.name,
            d.description__value AS description,
            d.weight,
            h.parent_target_id AS parent_id
        FROM taxonomy_term_data t
        JOIN taxonomy_term_field_data d ON t.tid = d.tid
        LEFT JOIN taxonomy_term__parent h ON t.tid = h.entity_id
        WHERE t.vid = %s
        ORDER BY d.weight, t.tid
        """,
        (vocabulary,),
    )


def get_node_field_values(content_type: str, nid: int, field_name: str) -> list[Any]:
    """Read raw field values from the node__<field_name> DB table."""
    table = f"node__{field_name}"
    column_prefix = field_name
    try:
        rows = db.fetchall(
            f"SELECT * FROM `{table}` WHERE entity_id = %s AND deleted = 0 ORDER BY delta",
            (nid,),
        )
        results = []
        for row in rows:
            # Try common column naming patterns
            for suffix in ("value", "target_id", "uri", "fid"):
                col = f"{column_prefix}_{suffix}"
                if col in row:
                    results.append(row[col])
                    break
        return results
    except Exception:
        return []


def list_nodes_via_api(
    api: DrupalApiClient,
    node_type: str,
    page_size: int = 50,
) -> list[dict]:
    """
    Page through all nodes of a given type via Drupal JSON:API.
    Returns a flat list of JSON:API resource objects.
    """
    offset = 0
    all_nodes: list[dict] = []
    while True:
        data = api.list_nodes(node_type, offset=offset, limit=page_size)
        items = data.get("data", [])
        if not items:
            break
        all_nodes.extend(items)
        # Check for next page link
        next_link = data.get("links", {}).get("next")
        if not next_link:
            break
        offset += page_size
    logger.debug(f"Fetched {len(all_nodes)} nodes of type '{node_type}' via REST API.")
    return all_nodes


def extract_node_attributes(node_resource: dict) -> dict:
    """Flatten a JSON:API node resource into a simple dict."""
    attrs = node_resource.get("attributes", {})
    relationships = node_resource.get("relationships", {})
    nid_val = attrs.get("drupal_internal__nid")
    return {
        "nid": nid_val,
        "uuid": node_resource.get("id"),
        "title": attrs.get("title", ""),
        "status": attrs.get("status", False),
        "created": attrs.get("created"),
        "changed": attrs.get("changed"),
        "body": clean_html((attrs.get("body") or {}).get("value", "") or ""),
        "body_summary": (attrs.get("body") or {}).get("summary", ""),
        "_relationships": relationships,
        "_attributes": attrs,
    }
