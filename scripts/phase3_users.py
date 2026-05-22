"""Phase 3: Migrate Drupal roles and users to Directus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rich.console import Console
from rich.progress import track

from src import config
from src.state import StateTracker
from src.drupal.user_reader import get_roles, get_users, get_user_roles
from src.directus.client import DirectusClient
from src.directus.user_writer import (
    get_existing_roles,
    ensure_role,
    create_user,
)
from src.logger import get_logger

logger = get_logger("phase3")
console = Console()

_ADMIN_DRUPAL_ROLE = "administrator"
_ADMIN_DIRECTUS_ROLE = "Administrator"


def main() -> None:
    console.rule("[bold blue]Phase 3: Identity & Access Migration")
    state = StateTracker(config.STATE_FILE)
    client = DirectusClient()

    try:
        existing_roles = get_existing_roles(client)

        # ── Roles ──────────────────────────────────────────────────────────
        drupal_roles = get_roles()
        drupal_role_to_directus: dict[str, str] = {}

        for role in drupal_roles:
            rid: str = role["rid"]
            label: str = role["label"]

            if state.is_migrated("roles", rid):
                drupal_role_to_directus[rid] = state.get_directus_id("roles", rid)
                logger.debug(f"Role '{rid}' already migrated, skipping.")
                continue

            # Map Drupal administrator → existing Directus Administrator (don't duplicate)
            if rid == _ADMIN_DRUPAL_ROLE:
                directus_role_id = existing_roles.get(_ADMIN_DIRECTUS_ROLE)
                if not directus_role_id:
                    directus_role_id = ensure_role(client, _ADMIN_DIRECTUS_ROLE, existing_roles)
                    existing_roles[_ADMIN_DIRECTUS_ROLE] = directus_role_id
            else:
                directus_role_id = ensure_role(client, label, existing_roles)
                existing_roles[label] = directus_role_id

            state.mark_migrated("roles", rid, directus_role_id)
            state.save()
            drupal_role_to_directus[rid] = directus_role_id

        logger.info(f"Roles migrated: {len(drupal_role_to_directus)}")

        # ── Users ──────────────────────────────────────────────────────────
        users = get_users()
        migrated = 0
        skipped = 0

        for user in track(users, description="Migrating users..."):
            uid: int = user["uid"]
            email: str = user.get("email") or f"user{uid}@migrated.local"

            if state.is_migrated("users", uid):
                skipped += 1
                continue

            # Determine primary Directus role (use first role found; Directus is single-role)
            user_roles = get_user_roles(uid)
            role_id: str | None = None
            for r in user_roles:
                if r in drupal_role_to_directus:
                    role_id = drupal_role_to_directus[r]
                    break

            try:
                directus_uid = create_user(
                    client,
                    email=email,
                    username=user.get("username", f"user{uid}"),
                    role_id=role_id,
                )
                state.mark_migrated("users", uid, directus_uid)
                state.save()
                migrated += 1
            except Exception as e:
                logger.error(f"Failed to migrate user uid={uid} ({email}): {e}")
                continue

        console.print(f"[green]Users migrated: {migrated}[/green] | Skipped (already done): {skipped}")
        logger.info(f"Phase 3 complete. Migrated {migrated} users, skipped {skipped}.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
