"""Tests for operator expression parser."""

import pytest

from restack_gen.ir import Parallel, Resource, Sequence
from restack_gen.parser import (
    ParseError,
    TokenType,
    get_project_resources,
    parse,
    parse_and_validate,
    tokenize,
    validate_ir,
)


class TestTokenizer:
    """Tests for tokenizer."""

    def test_tokenize_simple_name(self):
        """Test tokenizing a simple name."""
        tokens = tokenize("Agent1")
        assert len(tokens) == 2  # NAME + EOF
        assert tokens[0].type == TokenType.NAME
        assert tokens[0].value == "Agent1"
        assert tokens[1].type == TokenType.EOF

    def test_tokenize_sequence_operator(self):
        """Test tokenizing sequence operator."""
        tokens = tokenize("Agent1 → Workflow1")
        assert len(tokens) == 4  # NAME ARROW NAME EOF
        assert tokens[0].type == TokenType.NAME
        assert tokens[1].type == TokenType.ARROW
        assert tokens[1].value == "→"
        assert tokens[2].type == TokenType.NAME
        assert tokens[3].type == TokenType.EOF

    def test_tokenize_parallel_operator(self):
        """Test tokenizing parallel operator."""
        tokens = tokenize("Agent1 ⇄ Agent2")
        assert len(tokens) == 4  # NAME PARALLEL NAME EOF
        assert tokens[0].type == TokenType.NAME
        assert tokens[1].type == TokenType.PARALLEL
        assert tokens[1].value == "⇄"
        assert tokens[2].type == TokenType.NAME
        assert tokens[3].type == TokenType.EOF

    def test_tokenize_conditional_operator(self):
        """Test tokenizing conditional operator."""
        tokens = tokenize("Agent1 →?")
        assert len(tokens) == 3  # NAME CONDITIONAL EOF
        assert tokens[0].type == TokenType.NAME
        assert tokens[1].type == TokenType.CONDITIONAL
        assert tokens[1].value == "→?"

    def test_tokenize_parentheses(self):
        """Test tokenizing parentheses."""
        tokens = tokenize("(Agent1 → Agent2)")
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[1].type == TokenType.NAME
        assert tokens[2].type == TokenType.ARROW
        assert tokens[3].type == TokenType.NAME
        assert tokens[4].type == TokenType.RPAREN
        assert tokens[5].type == TokenType.EOF

    def test_tokenize_with_whitespace(self):
        """Test that whitespace is properly ignored."""
        tokens = tokenize("  Agent1   →   Agent2  ")
        token_types = [t.type for t in tokens]
        assert token_types == [TokenType.NAME, TokenType.ARROW, TokenType.NAME, TokenType.EOF]

    def test_tokenize_names_with_underscores(self):
        """Test tokenizing names with underscores."""
        tokens = tokenize("data_processor → email_sender")
        assert tokens[0].value == "data_processor"
        assert tokens[2].value == "email_sender"

    def test_tokenize_names_with_numbers(self):
        """Test tokenizing names with numbers."""
        tokens = tokenize("Agent1 → Worker2 → Handler3")
        values = [t.value for t in tokens if t.type == TokenType.NAME]
        assert values == ["Agent1", "Worker2", "Handler3"]

    def test_tokenize_complex_expression(self):
        """Test tokenizing complex expression."""
        tokens = tokenize("(A → B) ⇄ (C → D) → E")
        token_types = [t.type for t in tokens[:-1]]  # exclude EOF
        expected = [
            TokenType.LPAREN,
            TokenType.NAME,
            TokenType.ARROW,
            TokenType.NAME,
            TokenType.RPAREN,
            TokenType.PARALLEL,
            TokenType.LPAREN,
            TokenType.NAME,
            TokenType.ARROW,
            TokenType.NAME,
            TokenType.RPAREN,
            TokenType.ARROW,
            TokenType.NAME,
        ]
        assert token_types == expected

    def test_tokenize_invalid_character(self):
        """Test that invalid characters raise error."""
        with pytest.raises(ParseError, match="Invalid character"):
            tokenize("Agent1 @ Agent2")

    def test_tokenize_position_tracking(self):
        """Test that token positions are correctly tracked."""
        tokens = tokenize("A → B")
        assert tokens[0].position == 0  # A
        assert tokens[1].position == 2  # →
        assert tokens[2].position == 4  # B


class TestParser:
    """Tests for parser."""

    def test_parse_single_resource(self):
        """Test parsing a single resource."""
        ir = parse("Agent1")
        assert isinstance(ir, Resource)
        assert ir.name == "Agent1"

    def test_parse_simple_sequence(self):
        """Test parsing simple sequence."""
        ir = parse("Agent1 → Workflow1")
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 2
        assert ir.nodes[0].name == "Agent1"
        assert ir.nodes[1].name == "Workflow1"

    def test_parse_simple_parallel(self):
        """Test parsing simple parallel."""
        ir = parse("Agent1 ⇄ Agent2")
        assert isinstance(ir, Parallel)
        assert len(ir.nodes) == 2
        assert ir.nodes[0].name == "Agent1"
        assert ir.nodes[1].name == "Agent2"

    def test_parse_sequence_with_three_nodes(self):
        """Test parsing sequence with three nodes."""
        ir = parse("A → B → C")
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 3
        assert [n.name for n in ir.nodes] == ["A", "B", "C"]

    def test_parse_parallel_with_three_nodes(self):
        """Test parsing parallel with three nodes."""
        ir = parse("A ⇄ B ⇄ C")
        assert isinstance(ir, Parallel)
        assert len(ir.nodes) == 3
        assert [n.name for n in ir.nodes] == ["A", "B", "C"]

    def test_parse_precedence_parallel_over_sequence(self):
        """Test that parallel binds tighter than sequence."""
        # A → B ⇄ C → D should parse as: A → (B ⇄ C) → D
        ir = parse("A → B ⇄ C → D")
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 3
        assert ir.nodes[0].name == "A"
        assert isinstance(ir.nodes[1], Parallel)
        assert ir.nodes[1].nodes[0].name == "B"
        assert ir.nodes[1].nodes[1].name == "C"
        assert ir.nodes[2].name == "D"

    def test_parse_parentheses_override_precedence(self):
        """Test that parentheses override precedence."""
        # (A → B) ⇄ (C → D) should parse as two sequences in parallel
        ir = parse("(A → B) ⇄ (C → D)")
        assert isinstance(ir, Parallel)
        assert len(ir.nodes) == 2
        assert isinstance(ir.nodes[0], Sequence)
        assert isinstance(ir.nodes[1], Sequence)
        assert ir.nodes[0].nodes[0].name == "A"
        assert ir.nodes[0].nodes[1].name == "B"
        assert ir.nodes[1].nodes[0].name == "C"
        assert ir.nodes[1].nodes[1].name == "D"

    def test_parse_nested_parentheses(self):
        """Test parsing nested parentheses."""
        ir = parse("((A → B) ⇄ C)")
        assert isinstance(ir, Parallel)
        assert isinstance(ir.nodes[0], Sequence)

    def test_parse_complex_expression(self):
        """Test parsing complex expression."""
        # Start → (Worker1 ⇄ Worker2) → Process → End
        ir = parse("Start → (Worker1 ⇄ Worker2) → Process → End")
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 4
        assert ir.nodes[0].name == "Start"
        assert isinstance(ir.nodes[1], Parallel)
        assert ir.nodes[2].name == "Process"
        assert ir.nodes[3].name == "End"

    def test_parse_empty_expression(self):
        """Test that empty expression raises error."""
        with pytest.raises(ParseError, match="Empty expression"):
            parse("")

        with pytest.raises(ParseError, match="Empty expression"):
            parse("   ")

    def test_parse_missing_closing_paren(self):
        """Test error for missing closing parenthesis."""
        with pytest.raises(ParseError, match="Expected RPAREN"):
            parse("(A → B")

    def test_parse_unexpected_closing_paren(self):
        """Test error for unexpected closing parenthesis."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("A → B)")

    def test_parse_trailing_operator(self):
        """Test error for trailing operator."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("A → B →")

    def test_parse_leading_operator(self):
        """Test error for leading operator."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("→ A → B")

    def test_parse_double_operator(self):
        """Test error for double operator."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("A → → B")


class TestGetProjectResources:
    """Tests for get_project_resources function."""

    def test_get_resources_outside_project(self, tmp_path, monkeypatch):
        """Test error when not in a project."""
        # Create empty temp directory (no pyproject.toml)
        monkeypatch.chdir(tmp_path)
        with pytest.raises(RuntimeError, match="Not in a restack-gen project"):
            get_project_resources()

    def test_get_resources_in_project(self, tmp_path, monkeypatch):
        """Test getting resources from a project."""
        # Create project structure
        project_name = "testproject"
        project_root = tmp_path / "testproject"
        project_root.mkdir()

        # Create pyproject.toml
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        # Create src directory structure
        src_dir = project_root / "src" / project_name
        src_dir.mkdir(parents=True)

        # Create agents
        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "data_collector.py").write_text("class DataCollectorAgent: pass")
        (agents_dir / "processor.py").write_text("class ProcessorAgent: pass")

        # Create workflows
        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "email_workflow.py").write_text("class EmailWorkflowWorkflow: pass")

        # Create functions
        functions_dir = src_dir / "functions"
        functions_dir.mkdir()
        (functions_dir / "transform.py").write_text("def transform(): pass")
        (functions_dir / "validate_data.py").write_text("def validate_data(): pass")

        # Change to project directory
        monkeypatch.chdir(project_root)

        resources = get_project_resources()

        assert "DataCollectorAgent" in resources
        assert resources["DataCollectorAgent"] == "agent"
        assert "ProcessorAgent" in resources
        assert resources["ProcessorAgent"] == "agent"
        assert "EmailWorkflowWorkflow" in resources
        assert resources["EmailWorkflowWorkflow"] == "workflow"
        assert "transform" in resources
        assert resources["transform"] == "function"
        assert "validate_data" in resources
        assert resources["validate_data"] == "function"


class TestValidateIR:
    """Tests for validate_ir function."""

    def test_validate_outside_project(self, tmp_path, monkeypatch):
        """Test validation fails outside project."""
        # Create empty temp directory (no pyproject.toml)
        monkeypatch.chdir(tmp_path)
        ir = Resource("Test", "agent")
        valid, error = validate_ir(ir)
        assert not valid
        assert "Not in a restack-gen project" in error

    def test_validate_unknown_resource(self, tmp_path, monkeypatch):
        """Test validation fails for unknown resource."""
        # Create minimal project
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")
        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        monkeypatch.chdir(project_root)

        ir = Resource("NonExistent", "unknown")
        valid, error = validate_ir(ir)
        assert not valid
        assert "not found in project" in error

    def test_validate_existing_resource(self, tmp_path, monkeypatch):
        """Test validation succeeds for existing resource."""
        # Create project with one agent
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "test.py").write_text("class TestAgent: pass")

        monkeypatch.chdir(project_root)

        ir = Resource("TestAgent", "unknown")
        valid, error = validate_ir(ir)
        assert valid
        assert error is None
        # Check that resource type was updated
        assert ir.resource_type == "agent"

    def test_validate_sequence_with_valid_resources(self, tmp_path, monkeypatch):
        """Test validating sequence with valid resources."""
        # Create project with agent and workflow
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "data.py").write_text("class DataAgent: pass")

        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "process.py").write_text("class ProcessWorkflow: pass")

        monkeypatch.chdir(project_root)

        ir = Sequence(
            [
                Resource("DataAgent", "unknown"),
                Resource("ProcessWorkflow", "unknown"),
            ]
        )
        valid, error = validate_ir(ir)
        assert valid
        assert error is None
        assert ir.nodes[0].resource_type == "agent"
        assert ir.nodes[1].resource_type == "workflow"

    def test_validate_parallel_with_invalid_resource(self, tmp_path, monkeypatch):
        """Test validation fails with one invalid resource in parallel."""
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "valid.py").write_text("class ValidAgent: pass")

        monkeypatch.chdir(project_root)

        ir = Parallel(
            [
                Resource("ValidAgent", "unknown"),
                Resource("InvalidAgent", "unknown"),
            ]
        )
        valid, error = validate_ir(ir)
        assert not valid
        assert "InvalidAgent" in error
        assert "not found" in error


class TestParseAndValidate:
    """Tests for parse_and_validate function."""

    def test_parse_and_validate_success(self, tmp_path, monkeypatch):
        """Test successful parse and validate."""
        # Create project with resources
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "data.py").write_text("class DataAgent: pass")
        (agents_dir / "process.py").write_text("class ProcessAgent: pass")

        monkeypatch.chdir(project_root)

        ir = parse_and_validate("DataAgent → ProcessAgent")
        assert isinstance(ir, Sequence)
        assert ir.nodes[0].resource_type == "agent"
        assert ir.nodes[1].resource_type == "agent"

    def test_parse_and_validate_parse_error(self):
        """Test that parse errors are raised."""
        with pytest.raises(ParseError):
            parse_and_validate("Invalid → →")

    def test_parse_and_validate_validation_error(self, tmp_path, monkeypatch):
        """Test that validation errors are raised."""
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        monkeypatch.chdir(project_root)

        with pytest.raises(RuntimeError, match="Validation error"):
            parse_and_validate("NonExistent → AlsoNonExistent")


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_long_expression(self):
        """Test parsing very long expression."""
        # Create expression with 10 nodes
        names = [f"Node{i}" for i in range(10)]
        expr = " → ".join(names)
        ir = parse(expr)
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 10

    def test_deeply_nested_parentheses(self):
        """Test deeply nested parentheses."""
        expr = "((((A → B))))"
        ir = parse(expr)
        assert isinstance(ir, Sequence)
        assert ir.nodes[0].name == "A"
        assert ir.nodes[1].name == "B"

    def test_mixed_operators_complex(self):
        """Test complex mixed operators."""
        # (A ⇄ B) → (C ⇄ D) → E should create sequence of parallels
        ir = parse("(A ⇄ B) → (C ⇄ D) → E")
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 3
        assert isinstance(ir.nodes[0], Parallel)
        assert isinstance(ir.nodes[1], Parallel)
        assert isinstance(ir.nodes[2], Resource)

    def test_whitespace_variations(self):
        """Test various whitespace patterns."""
        expressions = [
            "A→B→C",
            "A → B → C",
            "A  →  B  →  C",
            "  A  →  B  →  C  ",
            "\nA\n→\nB\n→\nC\n",
        ]
        for expr in expressions:
            ir = parse(expr)
            assert isinstance(ir, Sequence)
            assert len(ir.nodes) == 3
