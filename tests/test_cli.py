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
    """Test doctor command prints results.

    Exit code may be 0 (all checks pass) or 1 (some checks fail).
    In CI or dev environments, checks like Restack engine connectivity may fail.
    """
    result = runner.invoke(app, ["doctor"])
    # Accept both success and failure exit codes
    assert result.exit_code in {0, 1}
    out = result.stdout.lower()
    assert "running doctor checks" in out
    assert "overall" in out


def test_run_server_command() -> None:
    """Test run:server command (requires server/service.py)."""
    result = runner.invoke(app, ["run:server"])
    # Will fail because we're not in a project directory with server/service.py
    assert result.exit_code == 1
    assert "service.py not found" in result.stdout


def test_generate_agent_in_project(tmp_path: Path) -> None:
    """Test generating an agent in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Create a minimal project structure
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        # Generate an agent
        result = runner.invoke(app, ["g", "agent", "TestAgent"])
        assert result.exit_code == 0
        assert "Generated agent" in result.stdout
        assert "TestAgent" in result.stdout

        # Files should be created somewhere in the project
        # Just verify the command succeeded
    finally:
        os.chdir(original_cwd)


def test_generate_workflow_in_project(tmp_path: Path) -> None:
    """Test generating a workflow in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "workflow", "TestWorkflow"])
        assert result.exit_code == 0
        assert "Generated workflow" in result.stdout
        assert "TestWorkflow" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_function_in_project(tmp_path: Path) -> None:
    """Test generating a function in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "function", "test_func"])
        assert result.exit_code == 0
        assert "Generated function" in result.stdout
        assert "test_func" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_pipeline_without_operators(tmp_path: Path) -> None:
    """Test that generating a pipeline without operators fails."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "pipeline", "TestPipeline"])
        assert result.exit_code == 1
        assert "requires --operators" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_pipeline_with_operators(tmp_path: Path) -> None:
    """Test generating a pipeline with operators."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        # First create the resources referenced in the pipeline
        runner.invoke(app, ["g", "agent", "A"])
        runner.invoke(app, ["g", "agent", "B"])

        result = runner.invoke(app, ["g", "pipeline", "TestPipeline", "--operators", "A → B"])
        assert result.exit_code == 0
        assert "Generated pipeline" in result.stdout
        assert "TestPipeline" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_tool_server_in_project(tmp_path: Path) -> None:
    """Test generating a tool server in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "tool-server", "TestTools"])
        assert result.exit_code == 0
        assert "Generated FastMCP tool server" in result.stdout
        assert "TestTools" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_llm_config_direct(tmp_path: Path) -> None:
    """Test generating LLM config with direct backend."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "llm-config"])
        assert result.exit_code == 0
        assert "Generated LLM router configuration" in result.stdout
        assert "OPENAI_API_KEY" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_llm_config_kong(tmp_path: Path) -> None:
    """Test generating LLM config with Kong backend."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "llm-config", "--backend", "kong"])
        assert result.exit_code == 0
        assert "Generated LLM router configuration" in result.stdout
        assert "KONG_GATEWAY_URL" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_prompt_in_project(tmp_path: Path) -> None:
    """Test generating a prompt in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "prompt", "TestPrompt", "--version", "1.0.0"])
        assert result.exit_code == 0
        assert "Generated prompt" in result.stdout
        assert "TestPrompt" in result.stdout
        assert "v1.0.0" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_unknown_resource_type(tmp_path: Path) -> None:
    """Test generating an unknown resource type."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "unknown", "TestResource"])
        assert result.exit_code == 1
        assert "Unknown resource type" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_without_name_for_agent(tmp_path: Path) -> None:
    """Test generating an agent without a name."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "agent"])
        # Exit code 1 from error, not 2 from typer
        assert result.exit_code == 1
        assert "Error" in result.stdout or "required" in result.stdout.lower()
    finally:
        os.chdir(original_cwd)


def test_doctor_verbose() -> None:
    """Test doctor command with verbose flag.

    Exit code may be 0 (all checks pass) or 1 (some checks fail).
    In CI or dev environments, checks like Restack engine connectivity may fail.
    """
    result = runner.invoke(app, ["doctor", "--verbose"])
    # Accept both success and failure exit codes
    assert result.exit_code in {0, 1}
    assert "running doctor checks" in result.stdout.lower()


def test_doctor_check_tools() -> None:
    """Test doctor command with check-tools flag.

    Exit code may be 0 (all checks pass) or 1 (some checks fail).
    In CI or dev environments, checks like Restack engine connectivity may fail.
    """
    result = runner.invoke(app, ["doctor", "--check-tools"])
    # Accept both success and failure exit codes
    assert result.exit_code in {0, 1}
    assert "running doctor checks" in result.stdout.lower()


def test_run_server_with_custom_config(tmp_path: Path) -> None:
    """Test run:server command with custom config."""
    result = runner.invoke(app, ["run:server", "--config", "custom.yaml"])
    # Will still fail without proper project structure, but tests the argument parsing
    assert result.exit_code == 1
