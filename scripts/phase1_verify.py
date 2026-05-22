"""Phase 1: Preflight connectivity check for all services."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.table import Table

from src.drupal import db
from src.drupal.api_client import DrupalApiClient
from src.directus.client import DirectusClient
from src.logger import get_logger

logger = get_logger("phase1")
console = Console()


def check_drupal_db() -> dict:
    info = db.test_connection()
    node_count = db.fetchone("SELECT COUNT(*) AS cnt FROM node")["cnt"]
    user_count = db.fetchone("SELECT COUNT(*) AS cnt FROM users_field_data WHERE status=1")["cnt"]
    file_count = db.fetchone("SELECT COUNT(*) AS cnt FROM file_managed WHERE status=1")["cnt"]
    return {
        "version": info.get("version", "?"),
        "database": info.get("db_name", "?"),
        "nodes": node_count,
        "active_users": user_count,
        "managed_files": file_count,
    }


def check_drupal_api(client: DrupalApiClient) -> bool:
    return client.ping()


def check_directus(client: DirectusClient) -> dict:
    info = client.server_info()
    return {
        "version": info.get("data", {}).get("directus", "?"),
        "node": info.get("data", {}).get("node", "?"),
    }


def main() -> None:
    console.rule("[bold blue]Drupal → Directus Migration Preflight Check")
    results = Table(title="Service Status", show_header=True, header_style="bold cyan")
    results.add_column("Service", style="bold")
    results.add_column("Status")
    results.add_column("Details")

    # Drupal DB
    try:
        db_info = check_drupal_db()
        results.add_row(
            "Drupal MySQL",
            "[green]OK[/green]",
            f"v{db_info['version']} | DB: {db_info['database']} | "
            f"Nodes: {db_info['nodes']} | Users: {db_info['active_users']} | Files: {db_info['managed_files']}",
        )
        logger.info(f"Drupal DB OK — {db_info}")
    except Exception as e:
        results.add_row("Drupal MySQL", "[red]FAIL[/red]", str(e))
        logger.error(f"Drupal DB connection failed: {e}")

    # Drupal REST API
    drupal_client = None
    try:
        drupal_client = DrupalApiClient()
        api_ok = check_drupal_api(drupal_client)
        status = "[green]OK[/green]" if api_ok else "[red]FAIL[/red]"
        results.add_row("Drupal REST API", status, "JSON:API endpoint reachable" if api_ok else "Not reachable")
        logger.info(f"Drupal REST API reachable: {api_ok}")
    except Exception as e:
        results.add_row("Drupal REST API", "[red]FAIL[/red]", str(e))
        logger.error(f"Drupal REST API failed: {e}")
    finally:
        if drupal_client:
            drupal_client.close()

    # Directus
    directus_client = None
    try:
        directus_client = DirectusClient()
        d_info = check_directus(directus_client)
        results.add_row(
            "Directus API",
            "[green]OK[/green]",
            f"Directus v{d_info['version']} | Node {d_info['node']}",
        )
        logger.info(f"Directus OK — {d_info}")
    except Exception as e:
        results.add_row("Directus API", "[red]FAIL[/red]", str(e))
        logger.error(f"Directus connection failed: {e}")
    finally:
        if directus_client:
            directus_client.close()

    console.print(results)
    console.rule()


if __name__ == "__main__":
    main()
