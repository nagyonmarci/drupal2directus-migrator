import json
import os
from typing import Optional

from src.logger import get_logger

logger = get_logger(__name__)

_ENTITY_TYPES = ("files", "users", "roles", "nodes", "terms", "blocks", "views")

_DEFAULT_STATE: dict = {t: {} for t in _ENTITY_TYPES}


class StateTracker:
    def __init__(self, path: str = "migration_state.json"):
        self._path = path
        self._state: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, "r") as f:
                self._state = json.load(f)
            logger.debug(f"Loaded state from {self._path}")
        else:
            self._state = {t: {} for t in _ENTITY_TYPES}
            logger.debug("No existing state file; starting fresh.")

        # Ensure all known entity type keys exist even if file predates them.
        for t in _ENTITY_TYPES:
            self._state.setdefault(t, {})

    def save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._state, f, indent=2)

    def is_migrated(self, entity_type: str, drupal_id: str | int) -> bool:
        return str(drupal_id) in self._state.get(entity_type, {})

    def mark_migrated(self, entity_type: str, drupal_id: str | int, directus_id: str) -> None:
        self._state.setdefault(entity_type, {})[str(drupal_id)] = str(directus_id)

    def get_directus_id(self, entity_type: str, drupal_id: str | int) -> Optional[str]:
        return self._state.get(entity_type, {}).get(str(drupal_id))

    def counts(self) -> dict[str, int]:
        return {t: len(v) for t, v in self._state.items()}
