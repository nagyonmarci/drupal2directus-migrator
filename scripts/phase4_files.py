"""Phase 4: Migrate Drupal managed files to Directus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from src import config
from src.state import StateTracker
from src.drupal.file_reader import get_managed_files, uri_to_url
from src.directus.client import DirectusClient
from src.directus.file_writer import download_file, upload_file
from src.logger import get_logger

logger = get_logger("phase4")
console = Console()


def main() -> None:
    console.rule("[bold blue]Phase 4: Media & File Migration")
    state = StateTracker(config.STATE_FILE)
    client = DirectusClient()

    try:
        files = get_managed_files()
        total = len(files)
        migrated = 0
        skipped = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Migrating files...", total=total)

            for i in range(0, total, config.BATCH_SIZE_FILES):
                batch = files[i : i + config.BATCH_SIZE_FILES]
                for f in batch:
                    fid: int = f["fid"]
                    filename: str = f["filename"]
                    uri: str = f["uri"]
                    mime: str = f["filemime"] or "application/octet-stream"

                    progress.update(task, advance=1, description=f"[cyan]{filename}[/cyan]")

                    if state.is_migrated("files", fid):
                        skipped += 1
                        continue

                    url = uri_to_url(uri)
                    if not url:
                        logger.warning(f"Skipping fid={fid}: cannot resolve URI '{uri}'")
                        failed += 1
                        continue

                    try:
                        content, detected_mime = download_file(url)
                        directus_file_id = upload_file(client, filename, content, detected_mime or mime, title=filename)
                        state.mark_migrated("files", fid, directus_file_id)
                        state.save()
                        migrated += 1
                    except Exception as e:
                        logger.error(f"Failed fid={fid} '{filename}': {e}")
                        failed += 1

        console.print(
            f"[green]Files migrated: {migrated}[/green] | "
            f"Skipped: {skipped} | [red]Failed: {failed}[/red]"
        )
        logger.info(f"Phase 4 complete. Migrated {migrated}, skipped {skipped}, failed {failed}.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
