"""Create Directus Presets from Drupal Views and generate query template files."""
import json
import os
from pathlib import Path
from src.directus.client import DirectusClient
from src.logger import get_logger

logger = get_logger(__name__)

_OUTPUT_DIR = Path("views_output")


def _ensure_output_dir() -> None:
    _OUTPUT_DIR.mkdir(exist_ok=True)


def _extract_base_table(view_config: dict) -> str:
    """Best-effort extraction of the Drupal View's base table (content type)."""
    return view_config.get("base_table", "node_field_data").replace("node_field_data", "").strip("_") or "node"


def _build_directus_filter(exposed_filters: dict) -> dict:
    """Convert Drupal exposed filter config to a Directus filter object."""
    directus_filter: dict = {}
    for field, opts in exposed_filters.items():
        if not isinstance(opts, dict):
            continue
        operator = opts.get("operator", "=")
        op_map = {"=": "_eq", "!=": "_neq", ">": "_gt", "<": "_lt", ">=": "_gte", "<=": "_lte", "contains": "_contains"}
        d_op = op_map.get(operator, "_eq")
        directus_filter[field] = {d_op: opts.get("value", "")}
    return directus_filter


def _build_sort(sorts: list) -> list[str]:
    """Convert Drupal sort criteria to Directus sort array."""
    result = []
    for s in sorts:
        if isinstance(s, dict):
            field = s.get("field", "created")
            order = s.get("order", "ASC")
            result.append(field if order == "ASC" else f"-{field}")
    return result or ["-created"]


def create_preset(client: DirectusClient, view_name: str, view_config: dict) -> str | None:
    """Create a Directus Preset from a Drupal View config. Returns preset ID."""
    label = view_config.get("label", view_name)
    base_table = _extract_base_table(view_config)

    displays = view_config.get("display", {})
    default_display = displays.get("default", {})
    display_options = default_display.get("display_options", {})

    exposed_filters = {}
    for fname, fdata in display_options.get("filters", {}).items():
        if isinstance(fdata, dict) and fdata.get("exposed"):
            exposed_filters[fname] = fdata

    sort_criteria = list(display_options.get("sorts", {}).values())
    limit = display_options.get("pager", {}).get("options", {}).get("items_per_page", 25)

    directus_filter = _build_directus_filter(exposed_filters)
    sort = _build_sort(sort_criteria)

    preset_payload = {
        "collection": base_table if base_table else "node",
        "layout": "tabular",
        "layout_query": {
            "tabular": {
                "fields": ["id", "title", "status", "created"],
                "sort": sort,
                "limit": limit,
                "filter": directus_filter,
            }
        },
        "layout_options": {},
        "user": None,
    }

    try:
        resp = client.post("/presets", preset_payload)
        preset_id: str = str(resp["data"]["id"])
        logger.info(f"Created Directus Preset for view '{view_name}' → {preset_id}")
        return preset_id
    except Exception as e:
        logger.error(f"Failed to create preset for '{view_name}': {e}")
        return None


def generate_query_file(view_name: str, view_config: dict, collection: str, limit: int, sort: list, directus_filter: dict) -> None:
    """Write a markdown query template file for a view."""
    _ensure_output_dir()
    label = view_config.get("label", view_name)
    description = view_config.get("description", "")

    filter_str = json.dumps(directus_filter, indent=4) if directus_filter else "{}"
    sort_str = ",".join(sort) if sort else "-created"
    rest_url = f"/items/{collection}?filter={filter_str}&sort={sort_str}&limit={limit}"

    graphql = f"""query {{
  {collection}(
    filter: {json.dumps(directus_filter)},
    sort: {json.dumps(sort)},
    limit: {limit}
  ) {{
    id
    title
    status
    created
  }}
}}"""

    content = f"""# View: {label}

**Machine name:** `{view_name}`
**Base collection:** `{collection}`
{f"> {description}" if description else ""}

## Directus REST Query

```
GET {rest_url}
```

## Directus GraphQL Query

```graphql
{graphql}
```
"""
    out_path = _OUTPUT_DIR / f"{view_name}.md"
    out_path.write_text(content, encoding="utf-8")
    logger.debug(f"Generated query file: {out_path}")


def generate_master_index(views: list[dict]) -> None:
    """Write a master views_documentation.md index."""
    _ensure_output_dir()
    lines = ["# Drupal Views → Directus Migration Documentation\n\n"]
    lines.append("| View | Label | Collection | File |\n")
    lines.append("|---|---|---|---|\n")
    for v in views:
        name = v["machine_name"]
        cfg = v.get("config", {})
        label = cfg.get("label", name)
        collection = _extract_base_table(cfg)
        lines.append(f"| `{name}` | {label} | `{collection}` | [{name}.md]({name}.md) |\n")

    out_path = _OUTPUT_DIR / "views_documentation.md"
    out_path.write_text("".join(lines), encoding="utf-8")
    logger.info(f"Written master index: {out_path}")
