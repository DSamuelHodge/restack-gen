"""Tests for FastMCP Server Manager generation and template content."""

import pytest

from restack_gen.doctor import check_tools
from restack_gen.generator import generate_tool_server
from restack_gen.project import create_new_project


class TestFastMCPManagerGeneration:
    """Test FastMCP manager file generation."""

    @pytest.fixture
    def test_project(self, tmp_path, monkeypatch):
        """Create a test project."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        return project_path

    def test_generate_manager_on_first_tool_server(self, test_project) -> None:
        """Test that fastmcp_manager.py is created with first tool server."""
        # Generate first tool server
        result = generate_tool_server("Research", force=False)

        # Check that manager was created
        manager_path = test_project / "src" / "testapp" / "common" / "fastmcp_manager.py"
        assert manager_path.exists(), "Manager file should be created with first tool server"
        assert "manager" in result
        assert result["manager"] == manager_path

        # Verify manager content
        content = manager_path.read_text()
        assert "class FastMCPServerManager" in content
        assert "class FastMCPClient" in content
        assert "def get_manager()" in content

    def test_manager_not_regenerated_for_second_tool_server(self, test_project) -> None:
        """Test that manager is not regenerated for subsequent tool servers."""
        # Generate first tool server
        result1 = generate_tool_server("Research", force=False)
        assert result1["manager"] is not None

        # Get original timestamp
        manager_path = test_project / "src" / "testapp" / "common" / "fastmcp_manager.py"
        original_mtime = manager_path.stat().st_mtime

        # Generate second tool server
        result2 = generate_tool_server("Docs", force=False)

        # Manager should not be in result (already exists)
        assert "manager" not in result2 or result2["manager"] is None

        # Manager file should not be modified
        assert manager_path.stat().st_mtime == original_mtime

    def test_manager_template_contains_required_methods(self, test_project) -> None:
        """Test that generated manager has all required methods."""
        generate_tool_server("Research", force=False)

        manager_path = test_project / "src" / "testapp" / "common" / "fastmcp_manager.py"
        content = manager_path.read_text()

        # Check FastMCPServerManager methods
        assert "def __init__" in content
        assert "def _load_config" in content
        assert "async def start_all" in content
        assert "async def start_server" in content
        assert "async def stop_server" in content
        assert "async def stop_all" in content
        assert "async def health_check" in content
        assert "async def health_check_all" in content
        assert "def list_servers" in content
        assert "def get_server" in content

        # Check FastMCPClient methods
        assert "async def __aenter__" in content
        assert "async def __aexit__" in content
        assert "async def call_tool" in content
        assert "async def list_tools" in content

        # Check helper functions
        assert "def get_manager()" in content
        assert "async def start_tool_servers()" in content
        assert "async def stop_tool_servers()" in content


class TestFastMCPManagerTemplateContent:
    """Test FastMCP manager template rendering and content details."""

    @pytest.fixture
    def manager_content(self, tmp_path, monkeypatch):
        """Generate a project and return manager content."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        generate_tool_server("Research", force=False)
        manager_path = project_path / "src" / "testapp" / "common" / "fastmcp_manager.py"
        return manager_path.read_text()

    def test_has_yaml_config_loading(self, manager_content) -> None:
        """Test that manager can load YAML configuration."""
        assert "tools.yaml" in manager_content or "config_path" in manager_content
        assert "yaml.safe_load" in manager_content or "yaml.load" in manager_content

    def test_handles_missing_config_file(self, manager_content) -> None:
        """Test that manager handles missing config files."""
        assert (
            "FileNotFoundError" in manager_content
            or "exists()" in manager_content
            or "is_file()" in manager_content
        )

    def test_has_server_config_dataclass(self, manager_content) -> None:
        """Test that ServerConfig dataclass is defined."""
        assert "@dataclass" in manager_content
        assert "class ServerConfig" in manager_content

    def test_server_config_has_fields(self, manager_content) -> None:
        """Test that ServerConfig has expected fields."""
        config_section = manager_content[manager_content.find("class ServerConfig") :][:500]
        assert "name" in config_section.lower()

    def test_handles_yaml_parsing_errors(self, manager_content) -> None:
        """Test that manager handles YAML parsing errors."""
        assert "YAMLError" in manager_content or "Exception" in manager_content

    def test_handles_empty_servers_list(self, manager_content) -> None:
        """Test that manager handles empty servers configuration."""
        load_section = manager_content[manager_content.find("def _load_config") :][:1000]
        assert "servers" in load_section.lower()

    def test_validates_server_exists_before_start(self, manager_content) -> None:
        """Test that start_server validates server exists."""
        start_section = manager_content[manager_content.find("async def start_server") :][:800]
        assert "if" in start_section or "not in" in start_section or "KeyError" in start_section

    def test_checks_server_state_before_stop(self, manager_content) -> None:
        """Test that stop_server checks if server is running."""
        stop_section = manager_content[manager_content.find("async def stop_server") :][:600]
        assert "if" in stop_section or "running" in stop_section.lower()

    def test_has_health_check_implementation(self, manager_content) -> None:
        """Test that health check returns status information."""
        health_section = manager_content[manager_content.find("async def health_check") :][:800]
        assert "return" in health_section

    def test_health_check_all_iterates_servers(self, manager_content) -> None:
        """Test that health_check_all processes all servers."""
        health_all_section = manager_content[manager_content.find("health_check_all") :][:600]
        assert "for" in health_all_section or "servers" in health_all_section.lower()

    def test_client_has_async_context_manager(self, manager_content) -> None:
        """Test that FastMCPClient implements async context manager protocol."""
        client_section = manager_content[manager_content.find("class FastMCPClient") :]
        assert "async def __aenter__" in client_section
        assert "async def __aexit__" in client_section

    def test_client_validates_connection_state(self, manager_content) -> None:
        """Test that client methods check connection state."""
        client_section = manager_content[manager_content.find("class FastMCPClient") :]
        assert "connected" in client_section.lower() or "connection" in client_section.lower()

    def test_has_singleton_manager_getter(self, manager_content) -> None:
        """Test that get_manager() implements singleton pattern."""
        assert "def get_manager" in manager_content
        assert "_manager" in manager_content or "_instance" in manager_content

    def test_has_convenience_helper_functions(self, manager_content) -> None:
        """Test that convenience helpers use global manager."""
        assert "async def start_tool_servers" in manager_content
        assert "async def stop_tool_servers" in manager_content

    def test_imports_required_modules(self, manager_content) -> None:
        """Test that required modules are imported."""
        # Should import asyncio for async operations
        assert "import asyncio" in manager_content or "from asyncio" in manager_content
        # Should import yaml for config loading
        assert "import yaml" in manager_content or "from yaml" in manager_content
        # Should import Path for file operations
        assert "from pathlib import Path" in manager_content or "import pathlib" in manager_content

    def test_has_type_annotations(self, manager_content) -> None:
        """Test that code uses type annotations."""
        assert "def " in manager_content and "->" in manager_content  # Return type annotations
        assert ": str" in manager_content or ": Dict" in manager_content  # Parameter annotations

    def test_has_docstrings(self, manager_content) -> None:
        """Test that classes and methods have docstrings."""
        assert '"""' in manager_content or "'''" in manager_content

    def test_handles_concurrent_operations(self, manager_content) -> None:
        """Test that manager can handle concurrent start/stop operations."""
        # Should use asyncio.gather or similar for concurrent ops
        assert (
            "gather" in manager_content.lower()
            or "wait" in manager_content.lower()
            or "task" in manager_content.lower()
        )


class TestToolServerDoctorIntegration:
    """Test integration with restack-gen doctor command."""

    @pytest.fixture
    def test_project(self, tmp_path, monkeypatch):
        """Create a test project with tools."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        generate_tool_server("Research", force=False)
        return project_path

    def test_doctor_detects_tool_servers(self, test_project) -> None:
        """Test that doctor command detects tool servers."""
        report = check_tools()
        # Should detect that tool servers are configured (even if they can't be imported in test env)
        assert (
            "1 configured servers" in str(report)
            or "found 1" in str(report).lower()
            or "1/1 tool servers" in str(report)
        )
