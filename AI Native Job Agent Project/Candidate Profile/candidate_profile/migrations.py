"""
Schema versioning and migration framework for Candidate Profile.
Reference: CONDUCTOR-CP-AD-v1.0 (Architecture Design §6, ADR-CP-5)
"""
from __future__ import annotations

from typing import Callable, Dict, Tuple, List, Any

CURRENT_SCHEMA_VERSION = "1.0.0"


class MigrationError(Exception):
    """Base exception for schema migration errors."""
    pass


class UnmigratableSchemaVersionError(MigrationError):
    """Raised when no valid migration path exists for a persisted profile's version."""
    pass


class MigrationRegistry:
    """Registry managing version-to-version migration functions."""

    def __init__(self) -> None:
        self._migrations: Dict[Tuple[str, str], Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register(
        self, from_version: str, to_version: str
    ) -> Callable[[Callable[[Dict[str, Any]], Dict[str, Any]]], Callable[[Dict[str, Any]], Dict[str, Any]]]:
        """Decorator to register a migration step function."""
        def decorator(
            func: Callable[[Dict[str, Any]], Dict[str, Any]]
        ) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
            self._migrations[(from_version, to_version)] = func
            return func

        return decorator

    def add_migration(
        self, from_version: str, to_version: str, func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """Register a migration function directly."""
        self._migrations[(from_version, to_version)] = func

    def get_migration_path(self, from_version: str, to_version: str) -> List[Tuple[str, str]]:
        """Find a sequence of migration steps from from_version to to_version using BFS."""
        if from_version == to_version:
            return []

        # Graph BFS
        queue: List[Tuple[str, List[Tuple[str, str]]]] = [(from_version, [])]
        visited = {from_version}

        while queue:
            current, path = queue.pop(0)
            if current == to_version:
                return path

            for (src, dst) in self._migrations:
                if src == current and dst not in visited:
                    visited.add(dst)
                    queue.append((dst, path + [(src, dst)]))

        raise UnmigratableSchemaVersionError(
            f"No migration path registered from schema version '{from_version}' to '{to_version}'."
        )

    def migrate(
        self, data: Dict[str, Any], from_version: str, to_version: str
    ) -> Dict[str, Any]:
        """Apply sequential migrations to transform data from from_version to to_version."""
        if from_version == to_version:
            return data

        path = self.get_migration_path(from_version, to_version)
        current_data = dict(data)

        for src, dst in path:
            migration_fn = self._migrations[(src, dst)]
            current_data = migration_fn(current_data)
            # Ensure metadata version is updated
            if "profile_metadata" in current_data and isinstance(current_data["profile_metadata"], dict):
                current_data["profile_metadata"]["schema_version"] = dst

        return current_data


# Global default registry
default_migration_registry = MigrationRegistry()


def migrate_profile(
    data: Dict[str, Any],
    target_version: str = CURRENT_SCHEMA_VERSION,
    registry: MigrationRegistry | None = None,
) -> Dict[str, Any]:
    """Migrate a raw candidate profile dictionary to target_version."""
    reg = registry or default_migration_registry
    metadata = data.get("profile_metadata", {})
    from_version = metadata.get("schema_version", "1.0.0")

    return reg.migrate(data, from_version=from_version, to_version=target_version)
