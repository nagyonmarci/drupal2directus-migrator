"""Phase 5: Migrate Drupal taxonomy terms and nodes to Directus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.progress import track

from src import config
from src.state import StateTracker
from src.drupal.schema_reader import get_content_types, get_fields_for_type, get_taxonomies, get_entity_reference_target
from src.drupal.content_reader import (
    get_taxonomy_terms,
    list_nodes_via_api,
    extract_node_attributes,
    get_node_field_values,
)
from src.drupal.api_client import DrupalApiClient
from src.directus.client import DirectusClient
from src.directus.content_writer import (
    create_taxonomy_term,
    create_node_item,
    create_m2m_relation,
)
from src.logger import get_logger

logger = get_logger("phase5")
console = Console()


def migrate_taxonomy(state: StateTracker, client: DirectusClient, taxonomies: list[dict]) -> None:
    for tax in taxonomies:
        vid = tax["vid"]
        terms = get_taxonomy_terms(vid)
        logger.info(f"Migrating {len(terms)} terms for vocabulary '{vid}'")
        for term in track(terms, description=f"[cyan]{vid}[/cyan] terms..."):
            try:
                create_taxonomy_term(client, state, vid, term)
            except Exception as e:
                logger.error(f"Failed term tid={term['tid']}: {e}")


def migrate_nodes(
    state: StateTracker,
    client: DirectusClient,
    drupal_api: DrupalApiClient,
    content_types: list[dict],
) -> None:
    for ct in content_types:
        machine_name = ct["type"]
        fields = get_fields_for_type(machine_name)

        logger.info(f"Fetching nodes for content type '{machine_name}'")
        try:
            raw_nodes = list_nodes_via_api(drupal_api, machine_name, page_size=config.BATCH_SIZE_CONTENT)
        except Exception as e:
            logger.error(f"Failed to fetch nodes for '{machine_name}' via REST: {e}")
            continue

        logger.info(f"Migrating {len(raw_nodes)} nodes of type '{machine_name}'")

        for raw in track(raw_nodes, description=f"[cyan]{machine_name}[/cyan] nodes..."):
            node = extract_node_attributes(raw)
            nid = node.get("nid")
            if not nid:
                continue

            if state.is_migrated("nodes", nid):
                continue

            # Build extra field values from DB field tables
            extra_fields: dict = {}
            m2m_relations: list[tuple] = []  # (junction_name, content_id, vocabulary, term_field, tid_list)

            for field in fields:
                field_name: str = field["field_name"]
                drupal_type: str = field["field_type"]
                if drupal_type == "entity_reference":
                    target = get_entity_reference_target(machine_name, field_name)
                    if target == "taxonomy_term":
                        vocab = field_name.replace("field_", "")
                        tids = get_node_field_values(machine_name, nid, field_name)
                        m2m_relations.append((f"{machine_name}_{vocab}", vocab, tids))
                        continue
                    else:
                        values = get_node_field_values(machine_name, nid, field_name)
                        if values:
                            ref_nid = values[0]
                            directus_ref_id = state.get_directus_id("nodes", ref_nid)
                            if directus_ref_id:
                                extra_fields[field_name] = directus_ref_id
                elif drupal_type in ("image", "file"):
                    values = get_node_field_values(machine_name, nid, field_name)
                    if values:
                        fid = values[0]
                        directus_file_id = state.get_directus_id("files", fid)
                        if directus_file_id:
                            extra_fields[field_name] = directus_file_id
                else:
                    values = get_node_field_values(machine_name, nid, field_name)
                    if values:
                        extra_fields[field_name] = values[0] if len(values) == 1 else values

            try:
                directus_id = create_node_item(client, state, machine_name, node, extra_fields)
            except Exception as e:
                logger.error(f"Failed node nid={nid}: {e}")
                continue

            # Create M2M junction records after node exists
            for (junction_name, vocab, tids) in m2m_relations:
                for tid in tids:
                    term_directus_id = state.get_directus_id("terms", tid)
                    if term_directus_id and directus_id:
                        create_m2m_relation(
                            client,
                            junction_name,
                            f"{machine_name}_id",
                            directus_id,
                            f"{vocab}_id",
                            term_directus_id,
                        )


def main() -> None:
    console.rule("[bold blue]Phase 5: Content & Relational Data Migration")
    state = StateTracker(config.STATE_FILE)
    client = DirectusClient()
    drupal_api = DrupalApiClient()

    try:
        taxonomies = get_taxonomies()
        migrate_taxonomy(state, client, taxonomies)

        content_types = get_content_types()
        migrate_nodes(state, client, drupal_api, content_types)

        logger.info("Phase 5 complete.")
        console.print("[green]Phase 5 content migration finished.[/green]")
    finally:
        client.close()
        drupal_api.close()


if __name__ == "__main__":
    main()
