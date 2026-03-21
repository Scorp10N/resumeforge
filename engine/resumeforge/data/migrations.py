"""Schema version upgrade functions for resume data files.

Migration functions follow the naming convention:
    migrate_<old_version>_to_<new_version>(data: dict[str, object]) -> dict[str, object]

The `migrate` entrypoint applies all required upgrades in order, returning
the fully-upgraded dict which the caller can then validate against the current
Pydantic model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from resumeforge.data.schema import SCHEMA_VERSION

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

MigrationFn = Callable[[dict[str, object]], dict[str, object]]


# ---------------------------------------------------------------------------
# Version ordering
# ---------------------------------------------------------------------------

# All known schema versions in ascending order.
_VERSIONS: list[str] = ["1.0"]


def _version_index(v: str) -> int:
    try:
        return _VERSIONS.index(v)
    except ValueError:
        raise ValueError(f"Unknown schema_version: {v!r}. Known versions: {_VERSIONS}") from None


# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------

# Maps (from_version, to_version) -> migration function.
_MIGRATIONS: dict[tuple[str, str], MigrationFn] = {}


def _register(from_v: str, to_v: str) -> Callable[[MigrationFn], MigrationFn]:
    """Decorator to register a migration function."""

    def decorator(fn: MigrationFn) -> MigrationFn:
        _MIGRATIONS[(from_v, to_v)] = fn
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Migration functions
#
# Add new ones here as the schema evolves, e.g.:
#
#   @_register("1.0", "1.1")
#   def migrate_1_0_to_1_1(data: dict[str, object]) -> dict[str, object]:
#       data = dict(data)
#       data.setdefault("new_field", "default_value")
#       data["schema_version"] = "1.1"
#       return data
# ---------------------------------------------------------------------------

# No migrations needed yet — version 1.0 is the initial schema.
# Example placeholder (commented out) for the next migration:
#
# @_register("1.0", "1.1")
# def migrate_1_0_to_1_1(data: dict[str, object]) -> dict[str, object]:
#     data = dict(data)
#     # Example: rename a field
#     if "old_field" in data:
#         data["new_field"] = data.pop("old_field")
#     data["schema_version"] = "1.1"
#     return data


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def migrate(data: dict[str, object]) -> dict[str, object]:
    """Upgrade *data* from its current schema_version to SCHEMA_VERSION.

    Args:
        data: Raw dict loaded from a JSON file (must contain ``schema_version``).

    Returns:
        A new dict at the current SCHEMA_VERSION, ready for Pydantic validation.

    Raises:
        ValueError: If the version is unknown or no migration path exists.
    """
    current = str(data.get("schema_version", "1.0"))
    target = SCHEMA_VERSION

    if current == target:
        return data

    from_idx = _version_index(current)
    to_idx = _version_index(target)

    if from_idx > to_idx:
        raise ValueError(
            f"Cannot downgrade schema from {current!r} to {target!r}."
        )

    result = dict(data)
    for i in range(from_idx, to_idx):
        step_from = _VERSIONS[i]
        step_to = _VERSIONS[i + 1]
        key = (step_from, step_to)
        if key not in _MIGRATIONS:
            raise ValueError(
                f"No migration registered for {step_from!r} -> {step_to!r}."
            )
        result = _MIGRATIONS[key](result)

    return result


def needs_migration(data: dict[str, object]) -> bool:
    """Return True if *data* is not at the current SCHEMA_VERSION."""
    return str(data.get("schema_version", "1.0")) != SCHEMA_VERSION


def migrate_file(path: Path) -> bool:
    """Migrate a JSON data file in-place if needed.

    Args:
        path: Path to the JSON file.

    Returns:
        True if the file was migrated, False if it was already current.

    Raises:
        ValueError: If the file has an unknown or unmigrateable version.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not needs_migration(raw):
        return False
    upgraded = migrate(raw)
    path.write_text(json.dumps(upgraded, indent=2, ensure_ascii=False), encoding="utf-8")
    return True
