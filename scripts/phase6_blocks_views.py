"""Phase 6: Migrate Drupal blocks; create Directus Presets and query docs from Views."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.progress import track

from src import config
from src.state import StateTracker
from src.drupal.views_reader import get_views, get_custom_blocks, get_block_region
from src.directus.client import DirectusClient
from src.directus.schema_writer import create_global_blocks_collection
from src.directus.views_writer import (
    create_preset,
    generate_query_file,
    generate_master_index,
    _extract_base_table,
    _build_directus_filter,
    _build_sort,
)
from src.logger import get_logger

logger = get_logger("phase6")
console = Console()


def migrate_blocks(state: StateTracker, client: DirectusClient) -> None:
    create_global_blocks_collection(client)
    blocks = get_custom_blocks()
    logger.info(f"Migrating {len(blocks)} custom blocks.")
    migrated = 0
    skipped = 0

    for block in track(blocks, description="Migrating blocks..."):
        bid = block["id"]
        if state.is_migrated("blocks", bid):
            skipped += 1
            continue

        region = get_block_region(block.get("uuid", "")) or ""
        payload = {
            "machine_name": block.get("machine_name") or f"block_{bid}",
            "title": block.get("machine_name") or f"Block {bid}",
            "body": block.get("body") or "",
            "region": region,
        }
        try:
            resp = client.post("/items/global_blocks", payload)
            directus_id = str(resp["data"]["id"])
            state.mark_migrated("blocks", bid, directus_id)
            state.save()
            migrated += 1
        except Exception as e:
            logger.error(f"Failed block id={bid}: {e}")

    console.print(f"[green]Blocks migrated: {migrated}[/green] | Skipped: {skipped}")


def migrate_views(state: StateTracker, client: DirectusClient) -> None:
    views = get_views()
    logger.info(f"Processing {len(views)} Drupal Views.")
    preset_count = 0
    file_count = 0

    for view in track(views, description="Processing views..."):
        name = view["machine_name"]
        cfg = view.get("config", {})

        # Create Directus Preset
        if not state.is_migrated("views", name):
            preset_id = create_preset(client, name, cfg)
            if preset_id:
                state.mark_migrated("views", name, preset_id)
                state.save()
                preset_count += 1

        # Always regenerate query files (idempotent — just overwrites)
        collection = _extract_base_table(cfg)
        displays = cfg.get("display", {})
        default_display = displays.get("default", {})
        display_options = default_display.get("display_options", {})
        exposed_filters = {
            fname: fdata
            for fname, fdata in display_options.get("filters", {}).items()
            if isinstance(fdata, dict) and fdata.get("exposed")
        }
        sort_criteria = list(display_options.get("sorts", {}).values())
        limit = display_options.get("pager", {}).get("options", {}).get("items_per_page", 25)
        directus_filter = _build_directus_filter(exposed_filters)
        sort = _build_sort(sort_criteria)

        generate_query_file(name, cfg, collection, limit, sort, directus_filter)
        file_count += 1

    generate_master_index(views)
    console.print(
        f"[green]Presets created: {preset_count}[/green] | "
        f"[green]Query files generated: {file_count}[/green] → views_output/"
    )


def main() -> None:
    console.rule("[bold blue]Phase 6: Blocks & Views Migration")
    state = StateTracker(config.STATE_FILE)
    client = DirectusClient()

    try:
        migrate_blocks(state, client)
        migrate_views(state, client)
        logger.info("Phase 6 complete.")
        console.print("[green]Phase 6 finished.[/green]")
    finally:
        client.close()


if __name__ == "__main__":
    main()
