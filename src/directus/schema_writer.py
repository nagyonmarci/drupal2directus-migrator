"""Create Directus collections and fields from a Drupal schema description."""
from src.directus.client import DirectusClient
from src.logger import get_logger

logger = get_logger(__name__)

# Fields added to every content collection
_STANDARD_FIELDS = [
    {"field": "drupal_nid", "type": "integer", "meta": {"hidden": True, "note": "Original Drupal node ID"}},
    {"field": "status", "type": "boolean", "meta": {"note": "Published status"}},
    {"field": "created", "type": "dateTime", "meta": {}},
    {"field": "changed", "type": "dateTime", "meta": {}},
    {"field": "title", "type": "string", "meta": {"required": True}},
]


def _collection_exists(client: DirectusClient, name: str) -> bool:
    try:
        client.get(f"/collections/{name}")
        return True
    except Exception:
        return False


def create_collection(client: DirectusClient, machine_name: str, human_name: str) -> None:
    if _collection_exists(client, machine_name):
        logger.debug(f"Collection '{machine_name}' already exists, skipping.")
        return

    payload = {
        "collection": machine_name,
        "meta": {"note": f"Migrated from Drupal content type: {human_name}"},
        "schema": {},
        "fields": _STANDARD_FIELDS,
    }
    client.post("/collections", payload)
    logger.info(f"Created collection: {machine_name}")


def add_field(client: DirectusClient, collection: str, field_name: str, directus_type: str, meta: dict | None = None) -> None:
    try:
        client.get(f"/fields/{collection}/{field_name}")
        logger.debug(f"Field '{collection}.{field_name}' already exists, skipping.")
        return
    except Exception:
        pass

    payload: dict = {
        "field": field_name,
        "type": directus_type,
        "meta": meta or {},
        "schema": {},
    }
    # File relations use uuid pointing to directus_files
    if directus_type == "uuid":
        payload["schema"] = {"is_nullable": True}
        payload["meta"]["special"] = ["file"]

    client.post(f"/fields/{collection}", payload)
    logger.info(f"Added field '{field_name}' ({directus_type}) to collection '{collection}'")


def create_m2m_junction(client: DirectusClient, collection: str, vocabulary: str) -> str:
    junction_name = f"{collection}_{vocabulary}"
    if _collection_exists(client, junction_name):
        logger.debug(f"Junction '{junction_name}' already exists, skipping.")
        return junction_name

    payload = {
        "collection": junction_name,
        "meta": {"hidden": True, "note": f"M2M junction: {collection} <-> {vocabulary}"},
        "schema": {},
        "fields": [
            {"field": f"{collection}_id", "type": "integer", "schema": {"is_nullable": False}},
            {"field": f"{vocabulary}_id", "type": "integer", "schema": {"is_nullable": False}},
        ],
    }
    client.post("/collections", payload)
    logger.info(f"Created M2M junction collection: {junction_name}")
    return junction_name


def create_taxonomy_collection(client: DirectusClient, vocabulary_id: str, name: str) -> None:
    if _collection_exists(client, vocabulary_id):
        logger.debug(f"Taxonomy collection '{vocabulary_id}' already exists, skipping.")
        return

    payload = {
        "collection": vocabulary_id,
        "meta": {"note": f"Drupal taxonomy: {name}"},
        "schema": {},
        "fields": [
            {"field": "drupal_tid", "type": "integer", "meta": {"hidden": True}},
            {"field": "name", "type": "string", "meta": {"required": True}},
            {"field": "description", "type": "text", "meta": {}},
            {"field": "weight", "type": "integer", "meta": {}},
            {"field": "parent_id", "type": "integer", "meta": {}},
        ],
    }
    client.post("/collections", payload)
    logger.info(f"Created taxonomy collection: {vocabulary_id}")


def create_global_blocks_collection(client: DirectusClient) -> None:
    if _collection_exists(client, "global_blocks"):
        logger.debug("Collection 'global_blocks' already exists, skipping.")
        return

    payload = {
        "collection": "global_blocks",
        "meta": {"note": "Migrated from Drupal custom blocks"},
        "schema": {},
        "fields": [
            {"field": "machine_name", "type": "string", "meta": {"required": True}, "schema": {"is_unique": True}},
            {"field": "title", "type": "string", "meta": {"required": True}},
            {"field": "body", "type": "text", "meta": {}},
            {"field": "region", "type": "string", "meta": {}},
        ],
    }
    client.post("/collections", payload)
    logger.info("Created 'global_blocks' collection.")
