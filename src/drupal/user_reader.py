"""Read Drupal 10 users and roles from the database."""
from src.drupal import db
from src.logger import get_logger

logger = get_logger(__name__)


def get_roles() -> list[dict]:
    """Return all Drupal roles (excluding built-ins)."""
    rows = db.fetchall(
        "SELECT rid, label FROM user_role WHERE rid NOT IN ('anonymous', 'authenticated') ORDER BY rid"
    )
    logger.debug(f"Found {len(rows)} custom roles.")
    return rows


def get_users() -> list[dict]:
    """Return all active Drupal users (uid > 0 = skip anonymous)."""
    rows = db.fetchall(
        """
        SELECT
            uid,
            name AS username,
            mail AS email,
            status,
            created,
            access AS last_access,
            timezone
        FROM users_field_data
        WHERE uid > 0
        ORDER BY uid
        """
    )
    logger.debug(f"Found {len(rows)} users.")
    return rows


def get_user_roles(uid: int) -> list[str]:
    """Return role IDs assigned to a given user."""
    rows = db.fetchall(
        "SELECT roles_target_id AS rid FROM user__roles WHERE entity_id = %s",
        (uid,),
    )
    return [row["rid"] for row in rows]
