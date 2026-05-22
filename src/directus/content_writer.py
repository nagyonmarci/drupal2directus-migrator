"""Create Directus items from migrated Drupal node data."""
from src.directus.client import DirectusClient
from src.state import StateTracker
from src.logger import get_logger

logger = get_logger(__name__)


def create_item(client: DirectusClient, collection: str, payload: dict) -> str:
    """Create an item in a Directus collection. Returns the new item's ID."""
    resp = client.post(f"/items/{collection}", payload)
    return str(resp["data"]["id"])


def create_taxonomy_term(
    client: DirectusClient,
    state: StateTracker,
    collection: str,
    term: dict,
) -> str | None:
    """Create a taxonomy term item in Directus. Returns Directus item ID."""
    tid = term["tid"]
    if state.is_migrated("terms", tid):
        return state.get_directus_id("terms", tid)

    parent_tid = term.get("parent_id")
    parent_directus_id = None
    if parent_tid and int(parent_tid) > 0:
        parent_directus_id = state.get_directus_id("terms", parent_tid)

    payload = {
        "drupal_tid": tid,
        "name": term["name"],
        "description": term.get("description") or "",
        "weight": term.get("weight") or 0,
        "parent_id": int(parent_directus_id) if parent_directus_id else None,
    }
    directus_id = create_item(client, collection, payload)
    state.mark_migrated("terms", tid, directus_id)
    state.save()
    logger.debug(f"Created taxonomy term tid={tid} → {directus_id}")
    return directus_id


def create_node_item(
    client: DirectusClient,
    state: StateTracker,
    collection: str,
    node: dict,
    extra_fields: dict | None = None,
) -> str | None:
    """Create a content node as a Directus item. Returns Directus item ID."""
    nid = node["nid"]
    if state.is_migrated("nodes", nid):
        return state.get_directus_id("nodes", nid)

    payload = {
        "drupal_nid": nid,
        "title": node["title"],
        "status": node["status"],
        "created": node.get("created"),
        "changed": node.get("changed"),
        "body": node.get("body") or "",
    }
    if extra_fields:
        payload.update(extra_fields)

    directus_id = create_item(client, collection, payload)
    state.mark_migrated("nodes", nid, directus_id)
    state.save()
    logger.debug(f"Created node nid={nid} → {directus_id}")
    return directus_id


def create_m2m_relation(
    client: DirectusClient,
    junction_collection: str,
    content_field: str,
    content_id: str,
    term_field: str,
    term_id: str,
) -> None:
    """Create a junction table record for a M2M taxonomy relation."""
    payload = {
        content_field: content_id,
        term_field: term_id,
    }
    try:
        client.post(f"/items/{junction_collection}", payload)
        logger.debug(f"Created M2M {junction_collection}: {content_id} <-> {term_id}")
    except Exception as e:
        logger.error(f"Failed to create M2M relation in '{junction_collection}': {e}")
