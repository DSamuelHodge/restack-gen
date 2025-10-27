"""Tests for console functionality."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from restack_gen.console import ConsoleError, _load_module, start_console
from restack_gen.project import create_new_project


@pytest.fixture
def test_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary test project."""
    create_new_project("testapp", tmp_path, force=False)
    project_path = tmp_path / "testapp"
    monkeypatch.chdir(project_path)
    return project_path


def test_load_module_success(tmp_path: Path) -> None:
    """Test loading a module from a file path."""
    # Create a simple module file
    module_file = tmp_path / "test_module.py"
    module_file.write_text("TEST_VAR = 'hello'")

    # Load the module
    module = _load_module(module_file)

    assert hasattr(module, "TEST_VAR")
    assert module.TEST_VAR == "hello"


def test_load_module_invalid_path() -> None:
    """Test loading module with invalid path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        _load_module(Path("/nonexistent/module.py"))


@patch("restack_gen.console.importlib.import_module")
def test_start_console_loads_settings(mock_import: Mock, test_project: Path) -> None:
    """Test that start_console loads settings module and launches console."""
    # Mock IPython module
    mock_ipython = MagicMock()
    mock_embed = MagicMock(side_effect=SystemExit(0))
    mock_ipython.embed = mock_embed

    # Mock the settings module
    mock_settings = MagicMock()
    mock_settings.settings = {"key": "value"}
    mock_import.return_value = mock_settings

    with patch.dict(sys.modules, {"IPython": mock_ipython}):
        with pytest.raises(SystemExit):
            start_console("config/dev.toml")

    # Verify settings were imported
    mock_import.assert_called_once_with("testapp.common.settings")

    # Verify embed was called with correct namespace
    call_args = mock_embed.call_args
    user_ns = call_args.kwargs["user_ns"]
    assert "settings" in user_ns
    assert "project_name" in user_ns
    assert "project_root" in user_ns
    assert user_ns["project_name"] == "testapp"
    assert user_ns["settings"] == {"key": "value"}


def test_start_console_missing_ipython(test_project: Path) -> None:
    """Test that missing IPython raises ConsoleError."""
    # Ensure IPython is not in sys.modules
    ipython_backup = sys.modules.pop("IPython", None)
    try:
        with pytest.raises(ConsoleError, match="IPython is not installed"):
            start_console("config/dev.toml")
    finally:
        # Restore IPython if it was there
        if ipython_backup:
            sys.modules["IPython"] = ipython_backup


def test_start_console_no_src_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing src/ directory raises ConsoleError."""
    # Mock IPython module
    mock_ipython = MagicMock()
    sys.modules["IPython"] = mock_ipython

    # Create project without src/ directory
    project_path = tmp_path / "empty_project"
    project_path.mkdir()
    monkeypatch.chdir(project_path)

    try:
        with pytest.raises(ConsoleError, match="No 'src/' directory found"):
            start_console("config/dev.toml")
    finally:
        sys.modules.pop("IPython", None)


def test_start_console_no_settings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing settings.py raises ConsoleError."""
    # Mock IPython module
    mock_ipython = MagicMock()
    sys.modules["IPython"] = mock_ipython

    # Create project with src/ but no settings.py
    project_path = tmp_path / "partial_project"
    project_path.mkdir()
    (project_path / "src").mkdir()
    (project_path / "src" / "testapp").mkdir()
    monkeypatch.chdir(project_path)

    try:
        with pytest.raises(ConsoleError, match="Could not determine project name/structure"):
            start_console("config/dev.toml")
    finally:
        sys.modules.pop("IPython", None)


@patch("restack_gen.console.importlib.import_module")
@patch("restack_gen.console.os.environ", {})
def test_start_console_sets_env_var(mock_import: Mock, test_project: Path) -> None:
    """Test that RESTACK_CONFIG environment variable is set."""
    import os

    # Mock IPython module
    mock_ipython = MagicMock()
    mock_embed = MagicMock(side_effect=SystemExit(0))
    mock_ipython.embed = mock_embed

    mock_settings = MagicMock()
    mock_settings.settings = {}
    mock_import.return_value = mock_settings

    with patch.dict(sys.modules, {"IPython": mock_ipython}):
        with pytest.raises(SystemExit):
            start_console("config/dev.toml")

    assert os.environ["RESTACK_CONFIG"] == "config/dev.toml"
