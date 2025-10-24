"""Tests for project generation functionality."""

from pathlib import Path

import pytest

from restack_gen.project import (
    create_new_project,
    validate_project_name,
)


class TestProjectNameValidation:
    """Tests for project name validation."""

    def test_valid_names(self) -> None:
        """Test that valid project names are accepted."""
        valid_names = ["myapp", "my_app", "app123", "myapp2"]
        for name in valid_names:
            is_valid, error = validate_project_name(name)
            assert is_valid, f"Expected '{name}' to be valid, but got error: {error}"

    def test_empty_name(self) -> None:
        """Test that empty names are rejected."""
        is_valid, error = validate_project_name("")
        assert not is_valid
        assert "cannot be empty" in error.lower()

    def test_uppercase_letters(self) -> None:
        """Test that uppercase letters are rejected."""
        is_valid, error = validate_project_name("MyApp")
        assert not is_valid
        assert "lowercase" in error.lower()

    def test_starts_with_number(self) -> None:
        """Test that names starting with numbers are rejected."""
        is_valid, error = validate_project_name("123app")
        assert not is_valid
        assert "start with a letter" in error.lower()

    def test_special_characters(self) -> None:
        """Test that special characters are rejected."""
        invalid_names = ["my-app", "my.app", "my app", "my@app"]
        for name in invalid_names:
            is_valid, error = validate_project_name(name)
            assert not is_valid, f"Expected '{name}' to be invalid"
            assert "lowercase letters" in error.lower()

    def test_python_keywords(self) -> None:
        """Test that Python keywords are rejected."""
        is_valid, error = validate_project_name("for")
        assert not is_valid
        assert "keyword" in error.lower()

    def test_reserved_words(self) -> None:
        """Test that reserved words are rejected."""
        reserved = ["test", "tests", "src", "lib"]
        for name in reserved:
            is_valid, error = validate_project_name(name)
            assert not is_valid, f"Expected '{name}' to be rejected as reserved"
            assert "reserved" in error.lower()


class TestProjectCreation:
    """Tests for project creation."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for test projects."""
        return tmp_path

    def test_creates_directory_structure(self, temp_project_dir: Path) -> None:
        """Test that project directory structure is created correctly."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        # Check that all expected directories exist
        expected_dirs = [
            project_path / "config",
            project_path / "server",
            project_path / "client",
            project_path / "src" / "testapp",
            project_path / "src" / "testapp" / "agents",
            project_path / "src" / "testapp" / "workflows",
            project_path / "src" / "testapp" / "functions",
            project_path / "src" / "testapp" / "common",
            project_path / "tests",
        ]

        for directory in expected_dirs:
            assert directory.exists(), f"Expected directory {directory} to exist"
            assert directory.is_dir(), f"Expected {directory} to be a directory"

    def test_creates_configuration_files(self, temp_project_dir: Path) -> None:
        """Test that configuration files are created."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        expected_files = [
            project_path / "pyproject.toml",
            project_path / "Makefile",
            project_path / ".gitignore",
            project_path / "README.md",
            project_path / "config" / "settings.yaml",
            project_path / "config" / ".env.example",
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"Expected file {file_path} to exist"
            assert file_path.is_file(), f"Expected {file_path} to be a file"
            assert file_path.stat().st_size > 0, f"Expected {file_path} to not be empty"

    def test_creates_common_modules(self, temp_project_dir: Path) -> None:
        """Test that common modules are created."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        common_dir = project_path / "src" / "testapp" / "common"
        expected_files = [
            common_dir / "retries.py",
            common_dir / "settings.py",
            common_dir / "compat.py",
            common_dir / "__init__.py",
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"Expected file {file_path} to exist"
            content = file_path.read_text(encoding="utf-8")
            if file_path.name != "__init__.py":
                assert len(content) > 0, f"Expected {file_path} to have content"
                # Check for @generated marker
                assert "@generated by restack-gen" in content

    def test_creates_service_file(self, temp_project_dir: Path) -> None:
        """Test that service.py is created with no resources."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        service_file = project_path / "server" / "service.py"
        assert service_file.exists()

        content = service_file.read_text(encoding="utf-8")
        assert "@generated by restack-gen" in content
        assert "workflows=[" in content
        assert "functions=[" in content

    def test_creates_init_files(self, temp_project_dir: Path) -> None:
        """Test that __init__.py files are created for package structure."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        init_files = [
            project_path / "src" / "testapp" / "__init__.py",
            project_path / "src" / "testapp" / "agents" / "__init__.py",
            project_path / "src" / "testapp" / "workflows" / "__init__.py",
            project_path / "src" / "testapp" / "functions" / "__init__.py",
        ]

        for init_file in init_files:
            assert init_file.exists(), f"Expected {init_file} to exist"

    def test_pyproject_toml_has_project_name(self, temp_project_dir: Path) -> None:
        """Test that pyproject.toml contains correct project name."""
        project_path = create_new_project("myproject", parent_dir=temp_project_dir)

        pyproject = project_path / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")

        assert 'name = "myproject"' in content
        assert "myproject" in content

    def test_settings_yaml_has_task_queue(self, temp_project_dir: Path) -> None:
        """Test that settings.yaml contains task queue configuration."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        settings = project_path / "config" / "settings.yaml"
        content = settings.read_text(encoding="utf-8")

        assert "task_queue:" in content
        assert "testapp" in content

    def test_env_example_has_prefix(self, temp_project_dir: Path) -> None:
        """Test that .env.example uses project name as prefix."""
        project_path = create_new_project("myapp", parent_dir=temp_project_dir)

        env_example = project_path / "config" / ".env.example"
        content = env_example.read_text(encoding="utf-8")

        assert "MYAPP_" in content

    def test_raises_error_for_invalid_name(self, temp_project_dir: Path) -> None:
        """Test that invalid project names raise ValueError."""
        with pytest.raises(ValueError, match="lowercase"):
            create_new_project("MyApp", parent_dir=temp_project_dir)

    def test_raises_error_if_directory_exists(self, temp_project_dir: Path) -> None:
        """Test that existing directory raises FileExistsError."""
        create_new_project("testapp", parent_dir=temp_project_dir)

        # Try to create again without force
        with pytest.raises(FileExistsError, match="already exists"):
            create_new_project("testapp", parent_dir=temp_project_dir, force=False)

    def test_force_overwrites_existing_directory(self, temp_project_dir: Path) -> None:
        """Test that force flag allows overwriting existing directory."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        # Create a file to verify overwrite
        marker_file = project_path / "marker.txt"
        marker_file.write_text("original", encoding="utf-8")

        # Create again with force
        create_new_project("testapp", parent_dir=temp_project_dir, force=True)

        # Verify standard files still exist
        assert (project_path / "pyproject.toml").exists()

    def test_readme_contains_project_info(self, temp_project_dir: Path) -> None:
        """Test that README.md contains project information."""
        project_path = create_new_project("coolapp", parent_dir=temp_project_dir)

        readme = project_path / "README.md"
        content = readme.read_text(encoding="utf-8")

        assert "coolapp" in content.lower()
        assert "restack" in content.lower()
        assert "@generated by restack-gen" in content

    def test_makefile_has_targets(self, temp_project_dir: Path) -> None:
        """Test that Makefile contains expected targets."""
        project_path = create_new_project("testapp", parent_dir=temp_project_dir)

        makefile = project_path / "Makefile"
        content = makefile.read_text(encoding="utf-8")

        expected_targets = ["setup", "install", "test", "lint", "fmt"]
        for target in expected_targets:
            assert f"{target}:" in content or f".PHONY: {target}" in content
