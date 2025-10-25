"""Tests for CLI commands."""

import os
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from restack_gen.cli import app

runner = CliRunner()


def test_version() -> None:
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "restack-gen" in result.stdout
    assert "1.0.0" in result.stdout


def test_help() -> None:
    """Test help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Rails-style scaffolding" in result.stdout


def test_new_command(tmp_path: Path) -> None:
    """Test new command creates a project."""
    # Change to temp directory
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["new", "testapp"])
        assert result.exit_code == 0
        assert "testapp" in result.stdout
        assert "Created project" in result.stdout

        # Verify project was created
        project_path = tmp_path / "testapp"
        assert project_path.exists()
        assert (project_path / "pyproject.toml").exists()
        assert (project_path / "server" / "service.py").exists()
    finally:
        os.chdir(original_cwd)


def test_new_command_invalid_name() -> None:
    """Test new command with invalid project name."""
    result = runner.invoke(app, ["new", "Invalid-Name"])
    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_generate_command() -> None:
    """Test generate command requires a project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory (no pyproject.toml)
        original_dir = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = runner.invoke(app, ["g", "agent", "TestAgent"])
            # Should fail because not in a project directory
            assert result.exit_code == 1
            assert "Not in a restack-gen project" in result.stdout
        finally:
            os.chdir(original_dir)


def test_doctor_command() -> None:
    """Test doctor command prints results and exits 0 in typical envs."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "running doctor checks" in out
    assert "overall" in out


def test_run_server_command() -> None:
    """Test run:server command (placeholder)."""
    result = runner.invoke(app, ["run:server"])
    assert result.exit_code == 0
    assert "server" in result.stdout.lower()
