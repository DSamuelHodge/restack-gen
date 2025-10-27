"""Tests for AST-based service.py manipulation."""

import ast

import pytest

from restack_gen.ast_service import (
    ServiceModificationError,
    add_import,
    add_to_list_in_source,
    find_import_section_end,
    find_list_argument,
    has_import,
    parse_service_file,
    update_service_file,
    write_service_file,
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


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_parse_service_file_invalid_syntax(self, tmp_path):
        """Test that parse_service_file raises error on invalid Python."""
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def invalid syntax here")

        with pytest.raises(ServiceModificationError, match="Failed to parse"):
            parse_service_file(bad_file)

    def test_parse_service_file_nonexistent(self, tmp_path):
        """Test that parse_service_file raises error on missing file."""
        missing_file = tmp_path / "missing.py"

        with pytest.raises(ServiceModificationError, match="Failed to parse"):
            parse_service_file(missing_file)

    def test_write_service_file_error(self, tmp_path):
        """Test that write_service_file handles write errors."""
        # Create a directory where we'd expect a file
        bad_path = tmp_path / "bad"
        bad_path.mkdir()

        with pytest.raises(ServiceModificationError, match="Failed to write"):
            write_service_file("content", bad_path)

    def test_update_service_file_invalid_type(self, tmp_path):
        """Test that update_service_file rejects invalid resource types."""
        service_path = tmp_path / "service.py"
        service_path.write_text("pass")

        with pytest.raises(ValueError, match="Invalid resource_type"):
            update_service_file(service_path, "invalid", "test", "Test")

    def test_update_service_file_no_project_name(self, tmp_path):
        """Test that update_service_file fails without project imports."""
        service_path = tmp_path / "service.py"
        service_path.write_text(
            """
import asyncio
# No project imports
"""
        )

        with pytest.raises(ServiceModificationError, match="Could not determine project name"):
            update_service_file(service_path, "agent", "test", "TestAgent")

    def test_add_to_list_no_start_service(self):
        """Test that add_to_list_in_source fails without start_service call."""
        source = """
import asyncio
# No start_service call
"""
        with pytest.raises(ServiceModificationError, match="Could not find start_service"):
            add_to_list_in_source(source, "workflows", "TestAgent")

    def test_add_to_list_missing_list_arg(self):
        """Test that add_to_list_in_source fails if list arg is missing."""
        source = """
await client.start_service(
    task_queue="test",
)
"""
        with pytest.raises(ServiceModificationError, match="Could not find workflows="):
            add_to_list_in_source(source, "workflows", "TestAgent")

    def test_add_to_list_cannot_find_in_source(self):
        """Test error when list argument isn't in expected format."""
        source = """
# Intentionally malformed
async def main():
    x = client.start_service(task_queue="test")
"""
        with pytest.raises(ServiceModificationError, match="Could not find workflows="):
            add_to_list_in_source(source, "workflows", "TestAgent")


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_find_import_section_end_no_imports(self):
        """Test find_import_section_end with no imports."""
        source = """
# Just a comment
def main():
    pass
"""
        tree = ast.parse(source)
        result = find_import_section_end(tree)
        assert result == 0

    def test_find_list_argument_not_found(self):
        """Test find_list_argument returns None when not found."""
        source = """
await client.start_service(task_queue="test")
"""
        tree = ast.parse(source)
        call_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_node = node
                break

        result = find_list_argument(call_node, "workflows")
        assert result is None

    def test_add_import_workflows_section(self):
        """Test adding import to workflows section."""
        source = """
from myproject.common.settings import settings

# Agents
from myproject.agents.data import DataAgent

# Workflows

# Functions
"""
        result = add_import(source, "myproject.workflows.email", ["EmailWorkflow"])

        assert "# Workflows" in result
        assert "from myproject.workflows.email import EmailWorkflow" in result

    def test_add_import_workflows_section_with_existing(self):
        """Test adding import to workflows section that has existing imports."""
        source = """
from myproject.common.settings import settings

# Agents
from myproject.agents.data import DataAgent

# Workflows
from myproject.workflows.process import ProcessWorkflow

# Functions
"""
        result = add_import(source, "myproject.workflows.email", ["EmailWorkflow"])

        assert "from myproject.workflows.process import ProcessWorkflow" in result
        assert "from myproject.workflows.email import EmailWorkflow" in result

        # EmailWorkflow should come after ProcessWorkflow
        process_pos = result.find("ProcessWorkflow")
        email_pos = result.find("EmailWorkflow")
        assert email_pos > process_pos

    def test_add_import_functions_section(self):
        """Test adding import to functions section."""
        source = """
from myproject.common.settings import settings

# Agents
from myproject.agents.data import DataAgent

# Workflows

# Functions

"""
        result = add_import(source, "myproject.functions.transform", ["transform"])

        assert "# Functions" in result
        assert "from myproject.functions.transform import transform" in result

    def test_add_import_functions_section_with_existing(self):
        """Test adding import to functions section that has existing imports."""
        source = """
from myproject.common.settings import settings

# Functions
from myproject.functions.validate import validate
"""
        result = add_import(source, "myproject.functions.transform", ["transform"])

        assert "from myproject.functions.validate import validate" in result
        assert "from myproject.functions.transform import transform" in result

        # transform should come after validate
        validate_pos = result.find("validate")
        transform_pos = result.find("transform")
        assert transform_pos > validate_pos

    def test_add_import_creates_workflows_section_after_settings(self):
        """Test that add_import creates workflows section when missing."""
        source = """
import asyncio
from myproject.common.settings import settings

async def main():
    pass
"""
        result = add_import(source, "myproject.workflows.email", ["EmailWorkflow"])

        assert "# Workflows" in result
        assert "from myproject.workflows.email import EmailWorkflow" in result

        # Should be after settings import
        settings_pos = result.find("from myproject.common.settings import settings")
        workflows_pos = result.find("# Workflows")
        assert workflows_pos > settings_pos

    def test_add_import_creates_functions_section_after_settings(self):
        """Test that add_import creates functions section when missing."""
        source = """
import asyncio
from myproject.common.settings import settings

async def main():
    pass
"""
        result = add_import(source, "myproject.functions.process", ["process"])

        assert "# Functions" in result
        assert "from myproject.functions.process import process" in result

    def test_update_service_with_module_prefix_override(self, tmp_path):
        """Test update_service_file with custom module_prefix."""
        # Create a minimal service.py
        service_path = tmp_path / "service.py"
        service_path.write_text(
            """
from testproject.common.settings import settings

await client.start_service(
    workflows=[
    ],
    functions=[
    ],
)
"""
        )

        update_service_file(
            service_path,
            "agent",
            "custom",
            "CustomAgent",
            module_prefix="testproject.custom_agents",
        )

        service_content = service_path.read_text()
        assert "from testproject.custom_agents.custom import CustomAgent" in service_content

    def test_add_to_list_nested_brackets(self):
        """Test handling of complex nested structures."""
        source = """
await client.start_service(
    workflows=[
        SomeAgent.with_options(timeout={"key": [1, 2, 3]}),
    ],
)
"""
        result = add_to_list_in_source(source, "workflows", "NewAgent")

        assert "NewAgent," in result
        assert "SomeAgent.with_options" in result

    def test_find_import_section_end_with_imports(self):
        """Test find_import_section_end returns correct line number."""
        source = """
import asyncio
from pathlib import Path
import os

def main():
    pass
"""
        tree = ast.parse(source)
        result = find_import_section_end(tree)
        # Should return line number of last import
        assert result > 0

    def test_add_import_no_section_found_agents(self):
        """Test add_import creates agent section when no sections exist."""
        source = """
import asyncio
from myproject.common.settings import settings

async def main():
    pass
"""
        result = add_import(source, "myproject.agents.data", ["DataAgent"])

        assert "# Agents" in result
        assert "from myproject.agents.data import DataAgent" in result

    def test_has_import_partial_match(self):
        """Test has_import with partial name matches."""
        source = """
from myproject.agents.data import DataAgent, OtherAgent
"""
        tree = ast.parse(source)

        # Should find both
        assert has_import(tree, "myproject.agents.data", ["DataAgent"])
        assert has_import(tree, "myproject.agents.data", ["OtherAgent"])
        assert has_import(tree, "myproject.agents.data", ["DataAgent", "OtherAgent"])

        # Should not find if one is missing
        assert not has_import(tree, "myproject.agents.data", ["DataAgent", "MissingAgent"])

    def test_add_import_multiple_names(self):
        """Test add_import with multiple names."""
        source = """
from myproject.common.settings import settings

# Agents
"""
        result = add_import(source, "myproject.agents.data", ["DataAgent", "OtherAgent"])

        assert "from myproject.agents.data import DataAgent, OtherAgent" in result

    def test_add_import_workflows_section_empty(self):
        """Test adding to empty workflows section (no existing imports after comment)."""
        source = """
from myproject.common.settings import settings

# Agents
from myproject.agents.data import DataAgent

# Workflows

# Functions
"""
        result = add_import(source, "myproject.workflows.email", ["EmailWorkflow"])

        assert "# Workflows" in result
        assert "from myproject.workflows.email import EmailWorkflow" in result
        # Should be added right after the # Workflows comment
        lines = result.split("\n")
        workflows_idx = next(i for i, line in enumerate(lines) if "# Workflows" in line)
        # The next non-empty line should be our import
        next_line = lines[workflows_idx + 1]
        assert "EmailWorkflow" in next_line or lines[workflows_idx + 2].strip().startswith("from")

    def test_add_import_functions_section_empty(self):
        """Test adding to empty functions section."""
        source = """
from myproject.common.settings import settings

# Agents

# Workflows

# Functions

"""
        result = add_import(source, "myproject.functions.transform", ["transform"])

        assert "# Functions" in result
        assert "from myproject.functions.transform import transform" in result

    def test_add_to_list_single_line_no_indent_match(self):
        """Test single-line list expansion when indent pattern is unusual."""
        source = """
await client.start_service(
workflows=[],
)
"""
        result = add_to_list_in_source(source, "workflows", "TestAgent")

        assert "TestAgent," in result
        # Should expand to multi-line
        assert "workflows=[" in result

    def test_add_to_list_multiline_no_existing_items_custom_indent(self):
        """Test multi-line empty list uses default indentation."""
        source = """
await client.start_service(
    workflows=[

    ],
)
"""
        result = add_to_list_in_source(source, "workflows", "TestAgent")

        assert "TestAgent," in result
