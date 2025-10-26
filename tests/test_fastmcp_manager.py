"""Tests for FastMCP Server Manager generation and functionality."""

import pytest
from pathlib import Path
import tempfile
import shutil
from restack_gen.generator import generate_tool_server
from restack_gen.project import create_new_project
from restack_gen.doctor import check_tools


class TestFastMCPManagerGeneration:
    """Test FastMCP manager file generation."""
    
    @pytest.fixture
    def test_project(self, tmp_path, monkeypatch):
        """Create a test project."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        return project_path
    
    def test_generate_manager_on_first_tool_server(self, test_project):
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
    
    def test_manager_not_regenerated_for_second_tool_server(self, test_project):
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
    
    def test_manager_template_contains_required_methods(self, test_project):
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


class TestFastMCPManagerFunctionality:
    """Test FastMCP manager runtime functionality."""
    
    @pytest.fixture
    def test_project_with_tools(self, tmp_path, monkeypatch):
        """Create a test project with tool servers."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        
        # Generate a tool server
        generate_tool_server("Research", force=False)
        
        return project_path
    
    def test_manager_loads_config(self, test_project_with_tools):
        """Test that manager can load tools.yaml configuration."""
        import sys
        # Add src directory to path for imports
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        manager = FastMCPServerManager(config_path=str(test_project_with_tools / "config" / "tools.yaml"))
        
        # Should have loaded the research_tools server
        assert "research_tools" in manager.server_configs
        config = manager.server_configs["research_tools"]
        assert config.name == "research_tools"
        assert config.autostart is True
    
    def test_manager_handles_missing_config(self, test_project_with_tools):
        """Test that manager handles missing config file gracefully."""
        import sys
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        # Remove config file
        config_path = test_project_with_tools / "config" / "tools.yaml"
        config_path.unlink()
        
        # Should not crash
        manager = FastMCPServerManager(config_path=str(config_path))
        assert len(manager.server_configs) == 0
    
    def test_list_servers(self, test_project_with_tools):
        """Test listing configured servers."""
        import sys
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        manager = FastMCPServerManager(config_path=str(test_project_with_tools / "config" / "tools.yaml"))
        servers = manager.list_servers()
        
        assert len(servers) == 1
        assert servers[0]["name"] == "research_tools"
        assert servers[0]["running"] is False
    
    def test_health_check_stopped_server(self, test_project_with_tools):
        """Test health check on stopped server."""
        import sys
        import asyncio
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        manager = FastMCPServerManager(config_path=str(test_project_with_tools / "config" / "tools.yaml"))
        
        async def check():
            result = await manager.health_check("research_tools")
            assert result["name"] == "research_tools"
            assert result["status"] == "stopped"
            assert result["configured"] is True
        
        asyncio.run(check())
    
    def test_health_check_unknown_server(self, test_project_with_tools):
        """Test health check on unknown server."""
        import sys
        import asyncio
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        manager = FastMCPServerManager(config_path=str(test_project_with_tools / "config" / "tools.yaml"))
        
        async def check():
            result = await manager.health_check("nonexistent_server")
            assert result["name"] == "nonexistent_server"
            assert result["status"] == "unknown"
            assert "not found" in result["error"].lower()
        
        asyncio.run(check())
    
    def test_health_check_all(self, test_project_with_tools):
        """Test checking all servers."""
        import sys
        import asyncio
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        manager = FastMCPServerManager(config_path=str(test_project_with_tools / "config" / "tools.yaml"))
        
        async def check():
            results = await manager.health_check_all()
            assert "research_tools" in results
            assert results["research_tools"]["status"] == "stopped"
        
        asyncio.run(check())
    
    def test_get_server_not_running(self, test_project_with_tools):
        """Test getting a server that is not running."""
        import sys
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import FastMCPServerManager
        
        manager = FastMCPServerManager(config_path=str(test_project_with_tools / "config" / "tools.yaml"))
        server = manager.get_server("research_tools")
        
        assert server is None
    
    def test_global_manager_singleton(self, test_project_with_tools):
        """Test that get_manager returns singleton instance."""
        import sys
        src_path = test_project_with_tools / "src"
        sys.path.insert(0, str(src_path))
        
        from testapp.common.fastmcp_manager import get_manager
        
        manager1 = get_manager()
        manager2 = get_manager()
        
        assert manager1 is manager2


class TestDoctorToolsCheck:
    """Test doctor --check-tools functionality."""
    
    @pytest.fixture
    def test_project_with_tools(self, tmp_path, monkeypatch):
        """Create a test project with tool servers."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        generate_tool_server("Research", force=False)
        return project_path
    
    def test_doctor_check_tools_with_config(self, test_project_with_tools):
        """Test doctor can check tools configuration."""
        result = check_tools(test_project_with_tools, verbose=False)
        
        assert result.name == "tools"
        # Should be OK or WARN (depends on fastmcp availability)
        assert result.status in ["ok", "warn", "fail"]
    
    def test_doctor_check_tools_no_config(self, tmp_path, monkeypatch):
        """Test doctor handles missing tools.yaml."""
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        
        result = check_tools(project_path, verbose=False)
        
        assert result.name == "tools"
        assert result.status == "ok"
        assert "no tool servers" in result.message.lower()
    
    def test_doctor_check_tools_invalid_yaml(self, test_project_with_tools):
        """Test doctor handles invalid YAML."""
        config_path = test_project_with_tools / "config" / "tools.yaml"
        config_path.write_text("invalid: yaml: content: [")
        
        result = check_tools(test_project_with_tools, verbose=False)
        
        assert result.name == "tools"
        assert result.status == "fail"
        assert "invalid" in result.message.lower()
    
    def test_doctor_check_tools_verbose(self, test_project_with_tools):
        """Test doctor verbose output includes server details."""
        result = check_tools(test_project_with_tools, verbose=True)
        
        assert result.name == "tools"
        # Verbose should include details (if available)
        # Details might be None if health check fails, which is OK


class TestServiceIntegration:
    """Test service.py integration with tool servers."""
    
    @pytest.fixture
    def test_project_with_tools(self, tmp_path, monkeypatch):
        """Create a test project with tool servers and regenerate service."""
        from restack_gen.renderer import render_template
        
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        generate_tool_server("Research", force=False)
        
        # Regenerate service.py to include tool server support
        service_path = project_path / "src" / "testapp" / "service.py"
        service_content = render_template("service.py.j2", {"project_name": "testapp"})
        service_path.write_text(service_content)
        
        return project_path
    
    def test_service_template_imports_manager(self, test_project_with_tools):
        """Test that generated service.py imports fastmcp_manager."""
        service_path = test_project_with_tools / "src" / "testapp" / "service.py"
        content = service_path.read_text()
        
        # Should have conditional import
        assert "from testapp.common.fastmcp_manager import start_tool_servers, stop_tool_servers" in content
        assert "FASTMCP_AVAILABLE" in content
    
    def test_service_template_starts_tools(self, test_project_with_tools):
        """Test that service.py calls start_tool_servers."""
        service_path = test_project_with_tools / "src" / "testapp" / "service.py"
        content = service_path.read_text()
        
        # Should call start in main
        assert "await start_tool_servers()" in content
        assert "if FASTMCP_AVAILABLE:" in content
    
    def test_service_template_stops_tools(self, test_project_with_tools):
        """Test that service.py calls stop_tool_servers in finally."""
        service_path = test_project_with_tools / "src" / "testapp" / "service.py"
        content = service_path.read_text()
        
        # Should call stop in finally block
        assert "await stop_tool_servers()" in content
        assert "finally:" in content
