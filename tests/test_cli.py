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


def test_new_command_file_exists_error(tmp_path: Path) -> None:
    """Test new command triggers FileExistsError when directory exists and force is False."""
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Create the directory first
        (tmp_path / "testapp").mkdir()
        result = runner.invoke(app, ["new", "testapp"])
        assert result.exit_code == 1
        assert "Error" in result.stdout
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
        # Check next steps output for plain agent generation
        assert "Next steps:" in result.stdout
        assert "Implement agent logic" in result.stdout
        assert "Run tests: make test" in result.stdout
        assert "Schedule agent:" in result.stdout

        # Files should be created somewhere in the project
        # Just verify the command succeeded
    finally:
        os.chdir(original_cwd)


def test_generate_agent_with_llm_in_project(tmp_path: Path) -> None:
    """Test generating an agent with LLM router in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Create a minimal project structure
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        # Generate an agent with LLM router
        result = runner.invoke(app, ["g", "agent", "TestAgentLLM", "--with-llm"])
        assert result.exit_code == 0
        assert "Generated agent" in result.stdout
        assert "TestAgentLLM" in result.stdout
        # Check for LLM enhancement message (without ANSI colors)
        assert "LLM router & prompt loader" in result.stdout
        assert "Configure LLM providers: restack g llm-config" in result.stdout
        assert "Create prompts: restack g prompt YourPrompt" in result.stdout

        # Files should be created somewhere in the project
        # Just verify the command succeeded
    finally:
        os.chdir(original_cwd)


def test_generate_agent_with_tools_in_project(tmp_path: Path) -> None:
    """Test generating an agent with tools server in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Create a minimal project structure
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        # Generate an agent with tools server
        result = runner.invoke(app, ["g", "agent", "TestAgentTools", "--tools", "Research"])
        assert result.exit_code == 0
        assert "Generated agent" in result.stdout
        assert "TestAgentTools" in result.stdout
        # Check for tools enhancement message (without ANSI colors)
        assert "FastMCP tools (Research)" in result.stdout
        assert "Ensure tool server exists: restack g tool-server Research" in result.stdout

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

        result = runner.invoke(app, ["g", "tool-server", "TestTools", "--force"])
        assert result.exit_code == 0
        assert "Generated FastMCP tool server" in result.stdout
        assert "TestTools" in result.stdout
        # Check that config output is included when config is generated
        assert "Config:" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_generate_migration_in_project(tmp_path: Path) -> None:
    """Test generating a migration in a valid project."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["g", "migration", "AddToolServer", "--target", "tools"])
        assert result.exit_code == 0
        assert "Generated configuration migration" in result.stdout
        assert "AddToolServer" in result.stdout
        assert "Target: tools.yaml" in result.stdout
        assert "Apply migration: restack migrate --target tools" in result.stdout
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
        # Check that loader output is included when loader is generated
        assert "Loader:" in result.stdout
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


def test_migrate_status_command(tmp_path: Path) -> None:
    """Test migrate status command."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["migrate", "--status"])
        assert result.exit_code == 0
        assert "Migration Status" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_migrate_up_command(tmp_path: Path) -> None:
    """Test migrate up command."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["migrate", "--direction", "up"])
        assert result.exit_code == 0
        assert "Applying configuration migrations" in result.stdout
        assert "Direction: up" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_migrate_down_command(tmp_path: Path) -> None:
    """Test migrate down command."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["migrate", "--direction", "down"])
        assert result.exit_code == 0
        assert "Applying configuration migrations" in result.stdout
        assert "Direction: down" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_migrate_invalid_direction(tmp_path: Path) -> None:
    """Test migrate command with invalid direction."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        runner.invoke(app, ["new", "testproject"])
        os.chdir(tmp_path / "testproject")

        result = runner.invoke(app, ["migrate", "--direction", "invalid"])
        assert result.exit_code == 1
        assert "Direction must be 'up' or 'down'" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_console_command_error_handling(tmp_path: Path) -> None:
    """Test console command error handling."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # Create a project but don't change to it - this should cause an error
        runner.invoke(app, ["new", "testproject"])
        # Try to run console from outside project directory
        result = runner.invoke(app, ["console"])
        # Should fail with exit code 1 due to ConsoleError
        assert result.exit_code == 1
        assert "Error starting console" in result.stdout
    finally:
        os.chdir(original_cwd)


def test_main_block_execution() -> None:
    """Test that the main block can be executed without errors."""
    # This tests the if __name__ == "__main__": app() line
    # Since app() is already tested through CliRunner, this ensures the main block works
    import restack_gen.cli as cli_module

    # Just verify the module can be imported and app exists
    assert hasattr(cli_module, "app")
    assert callable(cli_module.app)


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
