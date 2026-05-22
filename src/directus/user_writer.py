"""Create Directus roles and users."""
import secrets
from src.directus.client import DirectusClient
from src.logger import get_logger

logger = get_logger(__name__)

_ADMIN_ROLE_NAME = "Administrator"


def get_existing_roles(client: DirectusClient) -> dict[str, str]:
    """Return map of role name -> role id for all existing Directus roles."""
    resp = client.get("/roles", params={"limit": -1, "fields": "id,name"})
    return {r["name"]: r["id"] for r in resp.get("data", [])}


def create_role(client: DirectusClient, name: str) -> str:
    """Create a Directus role and return its ID."""
    resp = client.post("/roles", {"name": name})
    role_id: str = resp["data"]["id"]
    logger.info(f"Created role '{name}' → {role_id}")
    return role_id


def ensure_role(client: DirectusClient, name: str, existing: dict[str, str]) -> str:
    """Return existing role ID or create and return a new one."""
    if name in existing:
        logger.debug(f"Role '{name}' already exists: {existing[name]}")
        return existing[name]
    return create_role(client, name)


def create_user(
    client: DirectusClient,
    email: str,
    username: str,
    role_id: str | None,
    extra: dict | None = None,
) -> str:
    """Create a Directus user with a random placeholder password. Returns user ID."""
    password = secrets.token_urlsafe(32)
    payload: dict = {
        "email": email,
        "first_name": username,
        "password": password,
        "status": "active",
    }
    if role_id:
        payload["role"] = role_id
    if extra:
        payload.update(extra)

    resp = client.post("/users", payload)
    user_id: str = resp["data"]["id"]
    logger.info(f"Created user '{email}' → {user_id}")
    return user_id
