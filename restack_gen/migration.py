"""Configuration migration management.

Provides tools for versioned, reversible configuration file changes.
"""

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class MigrationError(Exception):
    """Raised when a migration operation fails."""

    pass


@dataclass
class MigrationStatus:
    """Status of a single migration."""

    timestamp: str
    name: str
    applied: bool
    applied_at: str | None = None


class MigrationRunner:
    """Manages configuration migrations with state tracking."""

    def __init__(self, project_root: Path) -> None:
        """Initialize migration runner.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.migration_dir = project_root / "config" / "migrations"
        self.state_file = self.migration_dir / ".migration_state.json"

    def _load_state(self) -> dict[str, Any]:
        """Load migration state from file."""
        if not self.state_file.exists():
            return {"applied": []}
        try:
            with open(self.state_file, encoding="utf-8") as f:
                return cast(dict[str, Any], json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            raise MigrationError(f"Failed to load migration state: {e}") from e

    def _save_state(self, state: dict[str, Any]) -> None:
        """Save migration state to file."""
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except OSError as e:
            raise MigrationError(f"Failed to save migration state: {e}") from e

    def _get_migration_files(self, target: str | None = None) -> list[Path]:
        """Get sorted list of migration files.

        Args:
            target: Optional filter by target config (e.g., 'prompts')

        Returns:
            Sorted list of migration file paths
        """
        if not self.migration_dir.exists():
            return []

        files = [
            f
            for f in self.migration_dir.glob("*.py")
            if f.name != "__init__.py" and not f.name.startswith(".")
        ]

        if target:
            # Filter by target in filename (convention: timestamp_target_name.py)
            files = [f for f in files if target in f.stem.lower()]

        return sorted(files)

    def _parse_migration_name(self, filepath: Path) -> tuple[str, str]:
        """Parse timestamp and name from migration filename.

        Args:
            filepath: Path to migration file

        Returns:
            Tuple of (timestamp, name)
        """
        stem = filepath.stem
        parts = stem.split("_", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return stem, stem

    def _load_migration_module(self, filepath: Path) -> Any:
        """Dynamically load migration module.

        Args:
            filepath: Path to migration file

        Returns:
            Loaded migration class instance

        Raises:
            MigrationError: If module cannot be loaded
        """
        try:
            spec = importlib.util.spec_from_file_location(filepath.stem, filepath)
            if spec is None or spec.loader is None:
                raise MigrationError(f"Cannot load module spec from {filepath}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[filepath.stem] = module
            spec.loader.exec_module(module)

            # Find the migration class (first class defined in module)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and hasattr(attr, "up") and hasattr(attr, "down"):
                    return attr()

            raise MigrationError(f"No migration class found in {filepath}")

        except Exception as e:
            raise MigrationError(f"Failed to load migration {filepath.name}: {e}") from e

    def get_status(self, target: str | None = None) -> list[MigrationStatus]:
        """Get status of all migrations.

        Args:
            target: Optional filter by target config

        Returns:
            List of migration statuses
        """
        state = self._load_state()
        applied = set(state.get("applied", []))
        applied_at = state.get("applied_at", {})

        statuses = []
        for filepath in self._get_migration_files(target):
            timestamp, name = self._parse_migration_name(filepath)
            migration_id = filepath.stem
            statuses.append(
                MigrationStatus(
                    timestamp=timestamp,
                    name=name,
                    applied=migration_id in applied,
                    applied_at=applied_at.get(migration_id),
                )
            )

        return statuses

    def migrate_up(self, target: str | None = None, count: int | None = None) -> list[str]:
        """Apply pending migrations.

        Args:
            target: Optional filter by target config
            count: Optional limit number of migrations to apply

        Returns:
            List of applied migration names

        Raises:
            MigrationError: If migration fails
        """
        state = self._load_state()
        applied = set(state.get("applied", []))
        applied_at = state.get("applied_at", {})

        files = self._get_migration_files(target)
        pending = [f for f in files if f.stem not in applied]

        if count is not None:
            pending = pending[:count]

        applied_migrations = []
        for filepath in pending:
            migration = self._load_migration_module(filepath)
            try:
                migration.up()
                applied.add(filepath.stem)
                from datetime import datetime

                applied_at[filepath.stem] = datetime.now().isoformat()
                applied_migrations.append(filepath.stem)
            except Exception as e:
                raise MigrationError(f"Migration {filepath.name} failed: {e}") from e

        state["applied"] = list(applied)
        state["applied_at"] = applied_at
        self._save_state(state)

        return applied_migrations

    def migrate_down(self, target: str | None = None, count: int = 1) -> list[str]:
        """Rollback applied migrations.

        Args:
            target: Optional filter by target config
            count: Number of migrations to rollback (default: 1)

        Returns:
            List of rolled back migration names

        Raises:
            MigrationError: If rollback fails
        """
        state = self._load_state()
        applied = set(state.get("applied", []))
        applied_at = state.get("applied_at", {})

        files = self._get_migration_files(target)
        applied_files = [f for f in reversed(files) if f.stem in applied]

        to_rollback = applied_files[:count]

        rolled_back = []
        for filepath in to_rollback:
            migration = self._load_migration_module(filepath)
            try:
                migration.down()
                applied.discard(filepath.stem)
                applied_at.pop(filepath.stem, None)
                rolled_back.append(filepath.stem)
            except Exception as e:
                raise MigrationError(f"Rollback of {filepath.name} failed: {e}") from e

        state["applied"] = list(applied)
        state["applied_at"] = applied_at
        self._save_state(state)

        return rolled_back
