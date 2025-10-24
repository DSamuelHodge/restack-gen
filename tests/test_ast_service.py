"""Tests for AST-based service.py manipulation."""

import ast
import pytest
from pathlib import Path

from restack_gen.ast_service import (
    add_import,
    add_to_list_in_source,
    has_import,
    parse_service_file,
    update_service_file,
)
from restack_gen.project import create_new_project


class TestImportDetection:
    """Test import detection utilities."""

    def test_has_import_detects_existing(self):
        """Test that has_import correctly identifies existing imports."""
        source = """
from myproject.agents.data import DataAgent
from myproject.workflows.process import ProcessWorkflow
"""
        tree = ast.parse(source)

        assert has_import(tree, "myproject.agents.data", ["DataAgent"])
        assert has_import(tree, "myproject.workflows.process", ["ProcessWorkflow"])

    def test_has_import_returns_false_for_missing(self):
        """Test that has_import returns False for non-existent imports."""
        source = """
from myproject.agents.data import DataAgent
"""
        tree = ast.parse(source)

        assert not has_import(tree, "myproject.agents.researcher", ["ResearcherAgent"])
        assert not has_import(tree, "myproject.workflows.email", ["EmailWorkflow"])


class TestImportInsertion:
    """Test import insertion logic."""

    def test_add_import_creates_section(self):
        """Test that add_import creates section comment if missing."""
        source = """
import asyncio
from restack_ai import Restack
from myproject.common.settings import settings
"""
        result = add_import(source, "myproject.agents.data", ["DataAgent"], "# Agents")

        assert "# Agents" in result
        assert "from myproject.agents.data import DataAgent" in result

    def test_add_import_adds_to_existing_section(self):
        """Test that add_import adds to existing section."""
        source = """
# Agents
from myproject.agents.data import DataAgent
"""
        result = add_import(source, "myproject.agents.researcher", ["ResearcherAgent"], "# Agents")

        # Should add after DataAgent import
        assert "from myproject.agents.data import DataAgent" in result
        assert "from myproject.agents.researcher import ResearcherAgent" in result

        # ResearcherAgent should come after DataAgent
        data_pos = result.find("DataAgent")
        researcher_pos = result.find("ResearcherAgent")
        assert researcher_pos > data_pos

    def test_add_import_skips_duplicate(self):
        """Test that add_import doesn't add duplicate imports."""
        source = """
# Agents
from myproject.agents.data import DataAgent
"""
        result = add_import(source, "myproject.agents.data", ["DataAgent"], "# Agents")

        # Should not add duplicate
        assert result.count("from myproject.agents.data import DataAgent") == 1


class TestListModification:
    """Test list modification in service.py."""

    def test_add_to_single_line_empty_list(self):
        """Test converting single-line empty list to multi-line."""
        source = """
await client.start_service(
    workflows=[        ],
    functions=[        ],
    task_queue="test",
)
"""
        result = add_to_list_in_source(source, "workflows", "DataAgent")

        # Should convert to multi-line and add item
        assert "workflows=[" in result
        assert "        DataAgent," in result
        # Check that the closing bracket is on its own line
        lines = result.split("\n")
        workflows_start = next(i for i, line in enumerate(lines) if "workflows=[" in line)
        # Find closing bracket
        assert any(
            "],\n" in line or "]," in line for line in lines[workflows_start : workflows_start + 5]
        )

    def test_add_to_multiline_empty_list(self):
        """Test adding to multi-line empty list."""
        source = """
await client.start_service(
    workflows=[
    ],
    functions=[
    ],
)
"""
        result = add_to_list_in_source(source, "workflows", "DataAgent")

        assert "        DataAgent," in result
        assert "workflows=[" in result

    def test_add_to_list_with_existing_items(self):
        """Test adding to list that already has items."""
        source = """
await client.start_service(
    workflows=[
        ResearcherAgent,
    ],
    functions=[
    ],
)
"""
        result = add_to_list_in_source(source, "workflows", "DataAgent")

        # Should add after ResearcherAgent
        assert "ResearcherAgent," in result
        assert "DataAgent," in result

        # Check order
        researcher_pos = result.find("ResearcherAgent,")
        data_pos = result.find("DataAgent,")
        assert data_pos > researcher_pos

    def test_add_to_list_preserves_indentation(self):
        """Test that indentation matches existing items."""
        source = """
await client.start_service(
    workflows=[
        ResearcherAgent,
    ],
)
"""
        result = add_to_list_in_source(source, "workflows", "DataAgent")

        # Find the lines with items
        lines = result.split("\n")
        researcher_line = next(line for line in lines if "ResearcherAgent" in line)
        data_line = next(line for line in lines if "DataAgent" in line)

        # Should have same leading whitespace
        researcher_indent = len(researcher_line) - len(researcher_line.lstrip())
        data_indent = len(data_line) - len(data_line.lstrip())
        assert researcher_indent == data_indent

    def test_add_to_list_skips_duplicate(self):
        """Test that duplicate items aren't added."""
        source = """
await client.start_service(
    workflows=[
        DataAgent,
    ],
)
"""
        result = add_to_list_in_source(source, "workflows", "DataAgent")

        # Should not add duplicate
        assert result.count("DataAgent,") == 1


class TestServiceFileUpdate:
    """Test complete service file update workflow."""

    @pytest.fixture
    def test_project(self, tmp_path):
        """Create a test project."""
        project_path = tmp_path / "testproject"
        create_new_project("testproject", parent_dir=tmp_path, force=False)
        return project_path

    def test_update_service_file_agent(self, test_project):
        """Test updating service.py for agent."""
        service_path = test_project / "server" / "service.py"

        update_service_file(service_path, "agent", "data", "DataAgent")

        service_content = service_path.read_text()

        # Check import
        assert "from testproject.agents.data import DataAgent" in service_content
        # Check registration in workflows list
        assert "DataAgent," in service_content
        assert "workflows=[" in service_content

    def test_update_service_file_workflow(self, test_project):
        """Test updating service.py for workflow."""
        service_path = test_project / "server" / "service.py"

        update_service_file(service_path, "workflow", "email", "EmailWorkflow")

        service_content = service_path.read_text()

        # Check import
        assert "from testproject.workflows.email import EmailWorkflow" in service_content
        # Check registration in workflows list
        assert "EmailWorkflow," in service_content

    def test_update_service_file_function(self, test_project):
        """Test updating service.py for function."""
        service_path = test_project / "server" / "service.py"

        update_service_file(service_path, "function", "transform", "transform")

        service_content = service_path.read_text()

        # Check import
        assert "from testproject.functions.transform import transform" in service_content
        # Check registration in functions list
        assert "transform," in service_content
        assert "functions=[" in service_content

    def test_update_service_multiple_times(self, test_project):
        """Test that multiple updates work correctly."""
        service_path = test_project / "server" / "service.py"

        # Add multiple resources
        update_service_file(service_path, "agent", "data", "DataAgent")
        update_service_file(service_path, "workflow", "process", "ProcessWorkflow")
        update_service_file(service_path, "function", "transform", "transform")

        service_content = service_path.read_text()

        # All should be present
        assert "DataAgent," in service_content
        assert "ProcessWorkflow," in service_content
        assert "transform," in service_content

        # Check structure
        assert "workflows=[" in service_content
        assert "functions=[" in service_content

    def test_update_service_idempotent(self, test_project):
        """Test that updating twice doesn't create duplicates."""
        service_path = test_project / "server" / "service.py"

        # Add same resource twice
        update_service_file(service_path, "agent", "data", "DataAgent")
        update_service_file(service_path, "agent", "data", "DataAgent")

        service_content = service_path.read_text()

        # Should only appear once
        assert service_content.count("DataAgent,") == 1
        assert service_content.count("from testproject.agents.data import DataAgent") == 1
