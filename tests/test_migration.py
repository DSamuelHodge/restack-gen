"""Tests for configuration migration system."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from restack_gen.generator import GenerationError, generate_config_migration
from restack_gen.migration import MigrationError, MigrationRunner


class TestMigrationGeneration:
    """Tests for migration file generation."""

    def test_generate_migration_basic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test basic migration generation."""
        # Setup project structure
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        (tmp_path / "config").mkdir()
        monkeypatch.chdir(tmp_path)

        # Generate migration
        result = generate_config_migration("AddNewField", "prompts")

        # Verify file was created
        assert "migration" in result
        migration_file = result["migration"]
        assert migration_file.exists()
        assert migration_file.parent == tmp_path / "config" / "migrations"

        # Verify filename format (timestamp_name.py)
        assert migration_file.stem.endswith("_add_new_field")
        assert len(migration_file.stem.split("_")[0]) == 14  # timestamp length

        # Verify file content
        content = migration_file.read_text()
        assert "class AddNewField:" in content
        assert "def up(self)" in content
        assert "def down(self)" in content
        assert "prompts.yaml" in content

    def test_generate_migration_invalid_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test migration generation with invalid name."""
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        monkeypatch.chdir(tmp_path)

        with pytest.raises(GenerationError, match="Invalid migration name"):
            generate_config_migration("invalid-name", "prompts")

    def test_generate_migration_invalid_target(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test migration generation with invalid target."""
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        monkeypatch.chdir(tmp_path)

        with pytest.raises(GenerationError, match="Invalid migration target"):
            generate_config_migration("Test", "invalid_target")

    def test_generate_migration_duplicate_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test migration generation with duplicate name."""
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        monkeypatch.chdir(tmp_path)

        # Generate first migration
        generate_config_migration("AddField", "prompts")

        # Try to generate duplicate without force
        with pytest.raises(GenerationError, match="already exists"):
            generate_config_migration("AddField", "prompts")

    def test_generate_migration_duplicate_with_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test migration generation overwrites with force flag."""
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        monkeypatch.chdir(tmp_path)

        # Generate first migration
        result1 = generate_config_migration("AddField", "prompts")
        file1 = result1["migration"]

        # Generate again with force (new timestamp)
        import time

        time.sleep(1.0)  # Ensure different timestamp (second precision)
        result2 = generate_config_migration("AddField", "prompts", force=True)
        file2 = result2["migration"]

        # Should create new file with different timestamp
        assert file2.exists()
        assert file1.stem != file2.stem  # Different timestamps

    def test_generate_migration_not_in_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test migration generation outside project."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(GenerationError, match="Not in a restack-gen project"):
            generate_config_migration("Test", "prompts")


class TestMigrationRunner:
    """Tests for MigrationRunner functionality."""

    def test_runner_initialization(self, tmp_path: Path) -> None:
        """Test MigrationRunner initialization."""
        runner = MigrationRunner(tmp_path)
        assert runner.project_root == tmp_path
        assert runner.migration_dir == tmp_path / "config" / "migrations"
        assert runner.state_file == tmp_path / "config" / "migrations" / ".migration_state.json"

    def test_get_status_empty(self, tmp_path: Path) -> None:
        """Test get_status with no migrations."""
        runner = MigrationRunner(tmp_path)
        statuses = runner.get_status()
        assert statuses == []

    def test_get_status_with_migrations(self, tmp_path: Path) -> None:
        """Test get_status with migration files."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create migration files
        (migration_dir / "20250101000000_add_field.py").write_text("# migration")
        (migration_dir / "20250101000001_remove_field.py").write_text("# migration")

        runner = MigrationRunner(tmp_path)
        statuses = runner.get_status()

        assert len(statuses) == 2
        assert statuses[0].timestamp == "20250101000000"
        assert statuses[0].name == "add_field"
        assert statuses[0].applied is False
        assert statuses[1].timestamp == "20250101000001"
        assert statuses[1].name == "remove_field"

    def test_save_and_load_state(self, tmp_path: Path) -> None:
        """Test state persistence."""
        runner = MigrationRunner(tmp_path)

        state = {
            "applied": ["20250101000000_add_field"],
            "applied_at": {"20250101000000_add_field": "2025-01-01T00:00:00"},
        }
        runner._save_state(state)

        loaded = runner._load_state()
        assert loaded == state

    def test_save_state_file_error(self, tmp_path: Path) -> None:
        """Test saving state with file access error."""
        runner = MigrationRunner(tmp_path)
        state = {"applied": ["test"]}

        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(MigrationError, match="Failed to save migration state"):
                runner._save_state(state)

    def test_load_state_missing_file(self, tmp_path: Path) -> None:
        """Test loading state when file doesn't exist."""
        runner = MigrationRunner(tmp_path)
        state = runner._load_state()
        assert state == {"applied": []}

    def test_load_state_corrupted_json(self, tmp_path: Path) -> None:
        """Test loading state with corrupted JSON file."""
        runner = MigrationRunner(tmp_path)
        # Create corrupted JSON file
        runner.state_file.parent.mkdir(parents=True, exist_ok=True)
        runner.state_file.write_text("{invalid json")

        with pytest.raises(MigrationError, match="Failed to load migration state"):
            runner._load_state()

    def test_load_state_file_error(self, tmp_path: Path) -> None:
        """Test loading state with file access error."""
        runner = MigrationRunner(tmp_path)
        runner.state_file.parent.mkdir(parents=True, exist_ok=True)
        runner.state_file.write_text('{"applied": []}')

        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(MigrationError, match="Failed to load migration state"):
                runner._load_state()

    def test_get_migration_files_sorted(self, tmp_path: Path) -> None:
        """Test migration files are returned sorted."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create files in random order
        (migration_dir / "20250103000000_third.py").write_text("# migration")
        (migration_dir / "20250101000000_first.py").write_text("# migration")
        (migration_dir / "20250102000000_second.py").write_text("# migration")

        runner = MigrationRunner(tmp_path)
        files = runner._get_migration_files()

        assert len(files) == 3
        assert files[0].stem == "20250101000000_first"
        assert files[1].stem == "20250102000000_second"
        assert files[2].stem == "20250103000000_third"

    def test_get_migration_files_filtered(self, tmp_path: Path) -> None:
        """Test migration file filtering by target."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        (migration_dir / "20250101000000_prompts_add.py").write_text("# migration")
        (migration_dir / "20250102000000_tools_update.py").write_text("# migration")

        runner = MigrationRunner(tmp_path)
        prompts_files = runner._get_migration_files(target="prompts")

        assert len(prompts_files) == 1
        assert "prompts" in prompts_files[0].stem

    def test_parse_migration_name_no_underscore(self, tmp_path: Path) -> None:
        """Test _parse_migration_name with filename containing no underscore."""
        runner = MigrationRunner(tmp_path)
        filepath = Path("20250101000000.py")  # No underscore in name

        timestamp, name = runner._parse_migration_name(filepath)
        assert timestamp == "20250101000000"
        assert name == "20250101000000"

    def test_load_migration_module_spec_none(self, tmp_path: Path) -> None:
        """Test _load_migration_module when spec_from_file_location returns None."""
        runner = MigrationRunner(tmp_path)
        migration_file = tmp_path / "test_migration.py"
        migration_file.write_text(
            "class TestMigration:\n    def up(self): pass\n    def down(self): pass"
        )

        with patch("importlib.util.spec_from_file_location", return_value=None):
            with pytest.raises(MigrationError, match="Cannot load module spec"):
                runner._load_migration_module(migration_file)

    def test_load_migration_module_no_loader(self, tmp_path: Path) -> None:
        """Test _load_migration_module when spec has no loader."""
        runner = MigrationRunner(tmp_path)
        migration_file = tmp_path / "test_migration.py"
        migration_file.write_text(
            "class TestMigration:\n    def up(self): pass\n    def down(self): pass"
        )

        mock_spec = MagicMock()
        mock_spec.loader = None

        with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
            with pytest.raises(MigrationError, match="Cannot load module spec"):
                runner._load_migration_module(migration_file)

    def test_load_migration_module_no_class_found(self, tmp_path: Path) -> None:
        """Test _load_migration_module when no migration class with up/down methods is found."""
        runner = MigrationRunner(tmp_path)
        migration_file = tmp_path / "test_migration.py"
        migration_file.write_text("# No migration class here\n\ndef some_function():\n    pass")

        with pytest.raises(MigrationError, match="No migration class found"):
            runner._load_migration_module(migration_file)

    def test_migrate_down_error_handling(self, tmp_path: Path) -> None:
        """Test migrate_down handles errors during rollback."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create migration that fails on down()
        migration_file = migration_dir / "20250101000000_failing_down.py"
        migration_file.write_text(
            """
class FailingDownMigration:
    def up(self):
        pass  # up succeeds

    def down(self):
        raise ValueError("Down migration failed")
"""
        )

        runner = MigrationRunner(tmp_path)

        # Apply the migration first
        applied = runner.migrate_up()
        assert len(applied) == 1

        # Try to rollback - should fail
        with pytest.raises(
            MigrationError, match="Rollback of 20250101000000_failing_down.py failed"
        ):
            runner.migrate_down()


class TestMigrationExecution:
    """Tests for migration execution (up/down)."""

    def create_test_migration(self, path: Path, name: str, config_field: str) -> None:
        """Helper to create a test migration file."""
        content = f'''"""Test migration."""
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "prompts.yaml"

class {name}:
    def _load_config(self):
        if not CONFIG_PATH.exists():
            return {{}}
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f) or {{}}

    def _save_config(self, data):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(data, f)

    def up(self):
        config = self._load_config()
        config["{config_field}"] = "test_value"
        self._save_config(config)

    def down(self):
        config = self._load_config()
        config.pop("{config_field}", None)
        self._save_config(config)
'''
        path.write_text(content)

    def test_migrate_up_single(self, tmp_path: Path) -> None:
        """Test applying a single migration."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create test migration
        migration_file = migration_dir / "20250101000000_add_field.py"
        self.create_test_migration(migration_file, "AddField", "test_field")

        runner = MigrationRunner(tmp_path)
        applied = runner.migrate_up()

        assert len(applied) == 1
        assert "20250101000000_add_field" in applied

        # Verify config was modified
        config_file = tmp_path / "config" / "prompts.yaml"
        assert config_file.exists()
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert config["test_field"] == "test_value"

        # Verify state was saved
        state = runner._load_state()
        assert "20250101000000_add_field" in state["applied"]

    def test_migrate_up_multiple(self, tmp_path: Path) -> None:
        """Test applying multiple migrations."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create multiple migrations
        migration1 = migration_dir / "20250101000000_add_field1.py"
        self.create_test_migration(migration1, "AddField1", "field1")
        migration2 = migration_dir / "20250101000001_add_field2.py"
        self.create_test_migration(migration2, "AddField2", "field2")

        runner = MigrationRunner(tmp_path)
        applied = runner.migrate_up()

        assert len(applied) == 2

        # Verify config has both fields
        config_file = tmp_path / "config" / "prompts.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert config["field1"] == "test_value"
        assert config["field2"] == "test_value"

    def test_migrate_up_with_count(self, tmp_path: Path) -> None:
        """Test applying limited number of migrations."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create multiple migrations
        for i in range(3):
            migration = migration_dir / f"2025010100000{i}_add_field{i}.py"
            self.create_test_migration(migration, f"AddField{i}", f"field{i}")

        runner = MigrationRunner(tmp_path)
        applied = runner.migrate_up(count=2)

        assert len(applied) == 2

    def test_migrate_down_single(self, tmp_path: Path) -> None:
        """Test rolling back a migration."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create and apply migration
        migration_file = migration_dir / "20250101000000_add_field.py"
        self.create_test_migration(migration_file, "AddField", "test_field")

        runner = MigrationRunner(tmp_path)
        runner.migrate_up()

        # Verify field exists
        config_file = tmp_path / "config" / "prompts.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert "test_field" in config

        # Rollback
        rolled_back = runner.migrate_down()
        assert len(rolled_back) == 1

        # Verify field was removed
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert "test_field" not in config

        # Verify state
        state = runner._load_state()
        assert "20250101000000_add_field" not in state["applied"]

    def test_migrate_down_multiple(self, tmp_path: Path) -> None:
        """Test rolling back multiple migrations."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create and apply multiple migrations
        for i in range(3):
            migration = migration_dir / f"2025010100000{i}_add_field{i}.py"
            self.create_test_migration(migration, f"AddField{i}", f"field{i}")

        runner = MigrationRunner(tmp_path)
        runner.migrate_up()

        # Rollback 2 migrations
        rolled_back = runner.migrate_down(count=2)
        assert len(rolled_back) == 2

        # Verify correct migrations were rolled back (most recent first)
        config_file = tmp_path / "config" / "prompts.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert "field0" in config  # First one still there
        assert "field1" not in config  # Rolled back
        assert "field2" not in config  # Rolled back

    def test_migrate_up_skip_applied(self, tmp_path: Path) -> None:
        """Test migrate_up skips already applied migrations."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        migration_file = migration_dir / "20250101000000_add_field.py"
        self.create_test_migration(migration_file, "AddField", "test_field")

        runner = MigrationRunner(tmp_path)

        # Apply once
        applied1 = runner.migrate_up()
        assert len(applied1) == 1

        # Try to apply again
        applied2 = runner.migrate_up()
        assert len(applied2) == 0  # Nothing to apply

    def test_migration_error_handling(self, tmp_path: Path) -> None:
        """Test error handling during migration."""
        migration_dir = tmp_path / "config" / "migrations"
        migration_dir.mkdir(parents=True)

        # Create migration that will fail
        migration_file = migration_dir / "20250101000000_bad_migration.py"
        migration_file.write_text(
            """
class BadMigration:
    def up(self):
        raise ValueError("Intentional error")

    def down(self):
        pass
"""
        )

        runner = MigrationRunner(tmp_path)

        with pytest.raises(MigrationError, match="Intentional error"):
            runner.migrate_up()


class TestMigrationIntegration:
    """Integration tests for the complete migration workflow."""

    def test_full_migration_workflow(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete workflow: generate -> apply -> rollback."""
        # Setup project
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        (tmp_path / "config").mkdir()
        monkeypatch.chdir(tmp_path)

        # Generate migration
        result = generate_config_migration("AddPromptField", "prompts")
        migration_file = result["migration"]

        # Modify migration to actually do something
        content = migration_file.read_text()
        # Add simple up/down logic
        content = content.replace(
            "# Example: Add a new setting",
            'if "test_field" not in config:\n            config["test_field"] = "value"\n            print("  -> Added test_field")',
        )
        content = content.replace(
            "# Example: Remove the setting",
            'if "test_field" in config:\n            del config["test_field"]\n            print("  -> Removed test_field")',
        )
        migration_file.write_text(content)

        # Apply migration
        runner = MigrationRunner(tmp_path)
        applied = runner.migrate_up()
        assert len(applied) == 1

        # Check status
        statuses = runner.get_status()
        assert len(statuses) == 1
        assert statuses[0].applied is True

        # Rollback
        rolled_back = runner.migrate_down()
        assert len(rolled_back) == 1

        # Check status again
        statuses = runner.get_status()
        assert statuses[0].applied is False

    def test_multiple_targets(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test migrations for different targets."""
        (tmp_path / "pyproject.toml").write_text('name = "testapp"')
        (tmp_path / "config").mkdir()
        monkeypatch.chdir(tmp_path)

        # Generate migrations for different targets
        generate_config_migration("UpdatePrompts", "prompts")
        generate_config_migration("UpdateTools", "tools")
        generate_config_migration("UpdateLLM", "llm-router")

        runner = MigrationRunner(tmp_path)

        # Get all statuses
        all_statuses = runner.get_status()
        assert len(all_statuses) == 3

        # Get filtered statuses
        prompts_statuses = runner.get_status(target="prompts")
        assert len(prompts_statuses) >= 1
        assert any("prompts" in s.name.lower() for s in prompts_statuses)
