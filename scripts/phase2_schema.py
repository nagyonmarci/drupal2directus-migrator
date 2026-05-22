"""Phase 2: Extract Drupal schema and create equivalent Directus collections."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.table import Table

from src.drupal.schema_reader import (
    get_content_types,
    get_all_fields,
    get_taxonomies,
    get_entity_reference_target,
    map_field_type,
)
from src.directus.client import DirectusClient
from src.directus.schema_writer import (
    create_collection,
    add_field,
    create_m2m_junction,
    create_taxonomy_collection,
    create_global_blocks_collection,
)
from src.logger import get_logger

logger = get_logger("phase2")
console = Console()


def dry_run() -> None:
    console.rule("[bold blue]Phase 2: Schema Migration (DRY RUN)")
    content_types = get_content_types()
    all_fields = get_all_fields()
    taxonomies = get_taxonomies()

    table = Table(title="Drupal Content Types", header_style="bold cyan")
    table.add_column("Machine Name")
    table.add_column("Label")
    table.add_column("Field Count")
    for ct in content_types:
        fields = all_fields.get(ct["type"], [])
        table.add_row(ct["type"], ct["name"], str(len(fields)))
    console.print(table)

    tax_table = Table(title="Taxonomy Vocabularies", header_style="bold cyan")
    tax_table.add_column("ID")
    tax_table.add_column("Name")
    for t in taxonomies:
        tax_table.add_row(t["vid"], t["name"])
    console.print(tax_table)
    logger.info(f"DRY RUN: found {len(content_types)} content types, {len(taxonomies)} vocabularies.")


def main() -> None:
    console.rule("[bold blue]Phase 2: Schema Migration")
    client = DirectusClient()

    try:
        # Taxonomy collections first (referenced by content types)
        taxonomies = get_taxonomies()
        for tax in taxonomies:
            create_taxonomy_collection(client, tax["vid"], tax["name"])

        # Content type collections + fields
        content_types = get_content_types()
        all_fields = get_all_fields()

        for ct in content_types:
            machine_name = ct["type"]
            create_collection(client, machine_name, ct["name"])

            fields = all_fields.get(machine_name, [])
            for field in fields:
                field_name: str = field["field_name"]
                drupal_type: str = field["field_type"]
                directus_type = map_field_type(drupal_type)
                meta: dict = {"note": field.get("label", "")}

                if drupal_type == "entity_reference":
                    target = get_entity_reference_target(machine_name, field_name)
                    if target == "taxonomy_term":
                        # Determine vocabulary from field settings; use field_name as fallback
                        vocabulary = field_name.replace("field_", "")
                        create_m2m_junction(client, machine_name, vocabulary)
                        logger.info(f"  M2M junction for {machine_name}.{field_name} → {vocabulary}")
                        continue
                    else:
                        directus_type = "integer"

                cardinality = field.get("cardinality", 1)
                if cardinality == -1 or cardinality > 1:
                    meta["note"] = f"{meta.get('note', '')} [multi-value]".strip()

                add_field(client, machine_name, field_name, directus_type, meta)

        # global_blocks collection for Phase 6
        create_global_blocks_collection(client)

        logger.info("Phase 2 complete.")
        console.print("[green]Phase 2 schema migration finished.[/green]")
    finally:
        client.close()


if __name__ == "__main__":
    main()
