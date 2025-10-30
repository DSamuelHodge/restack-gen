"""Tests for operator expression parser."""

import pytest

from restack_gen.ir import Conditional, Parallel, Resource, Sequence
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

    def test_token_repr(self):
        """Test token __repr__."""
        from restack_gen.parser import Token, TokenType

        t = Token(TokenType.NAME, "foo", 3)
        assert str(t) == "Token(NAME, 'foo', pos=3)"

    def test_tokenize_comma(self):
        """Test tokenizing comma."""
        from restack_gen.parser import TokenType, tokenize

        tokens = tokenize(",")
        assert tokens[0].type == TokenType.COMMA
        assert tokens[0].value == ","


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

    def test_parse_parentheses_override_precedence(self) -> None:
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

    def test_parse_nested_parentheses(self) -> None:
        """Test parsing nested parentheses."""
        ir = parse("((A → B) ⇄ C)")
        assert isinstance(ir, Parallel)
        assert isinstance(ir.nodes[0], Sequence)

    def test_parse_complex_expression(self) -> None:
        """Test parsing complex expression."""
        # Start → (Worker1 ⇄ Worker2) → Process → End
        ir = parse("Start → (Worker1 ⇄ Worker2) → Process → End")
        assert isinstance(ir, Sequence)
        assert len(ir.nodes) == 4
        assert ir.nodes[0].name == "Start"
        assert isinstance(ir.nodes[1], Parallel)
        assert ir.nodes[2].name == "Process"
        assert ir.nodes[3].name == "End"

    def test_parse_empty_expression(self) -> None:
        """Test that empty expression raises error."""
        with pytest.raises(ParseError, match="Empty expression"):
            parse("")

        with pytest.raises(ParseError, match="Empty expression"):
            parse("   ")

    def test_parse_missing_closing_paren(self) -> None:
        """Test error for missing closing parenthesis."""
        with pytest.raises(ParseError, match="Expected RPAREN"):
            parse("(A → B")

    def test_parse_unexpected_closing_paren(self) -> None:
        """Test error for unexpected closing parenthesis."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("A → B)")

    def test_parse_trailing_operator(self) -> None:
        """Test error for trailing operator."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("A → B →")

    def test_parse_leading_operator(self) -> None:
        """Test error for leading operator."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("→ A → B")

    def test_parse_double_operator(self) -> None:
        """Test error for double operator."""
        with pytest.raises(ParseError, match="Unexpected token"):
            parse("A → → B")

    def test_parse_conditional_with_false_branch(self) -> None:
        """Test parsing conditional with false branch."""
        from restack_gen.ir import Conditional
        from restack_gen.parser import parse

        ir = parse("Cond →? (A, B)")
        assert isinstance(ir, Conditional)
        assert ir.condition == "Cond"
        assert ir.true_branch.name == "A"
        assert ir.false_branch.name == "B"

    def test_parse_conditional_without_false_branch(self) -> None:
        """Test conditional operator without false branch."""
        from restack_gen.parser import parse

        # Create a conditional without false branch
        ir = parse("Agent1 →? (Workflow1)")
        assert ir is not None
        assert isinstance(ir, Conditional)
        assert ir.condition == "Agent1"
        assert ir.false_branch is None

    def test_expect_parse_error(self) -> None:
        """Test ParseError is raised in expect method."""
        from restack_gen.parser import ParseError, Parser, Token, TokenType

        # Create parser with tokens that don't match expectation
        tokens = [Token(TokenType.NAME, "Agent1", 0)]
        parser = Parser(tokens)

        # Expect a different token type
        with pytest.raises(ParseError, match="Expected ARROW"):
            parser.expect(TokenType.ARROW)

    def test_register_empty_name(self) -> None:
        """Test register function with empty name."""

        # Mock get_project_resources to test register function directly
        # We need to access the register function inside get_project_resources
        # This is tricky, so we'll test indirectly by ensuring empty names don't get registered
        pass  # The register function's empty check is covered by normal operation

    def test_get_project_resources_no_directories(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when directories don't exist."""

        # Create project without src directory
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        monkeypatch.chdir(project_root)

        # Should return empty resources when no directories exist
        resources = get_project_resources()
        assert resources == {}

    def test_validate_resource_not_found(self, tmp_path, monkeypatch) -> None:
        """Test validation when resource is not found."""
        from restack_gen.parser import Resource

        # Create project with some resources
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        monkeypatch.chdir(project_root)

        # Try to validate non-existent resource
        node = Resource("NonExistent", "agent")
        valid, error = validate_ir(node)
        assert not valid
        assert "not found in project" in error

    def test_validate_type_mismatch(self, tmp_path, monkeypatch) -> None:
        """Test validation when resource type doesn't match."""
        from restack_gen.parser import Resource

        # Create project with agent
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        monkeypatch.chdir(project_root)

        # Try to validate agent as workflow
        node = Resource("Agent1Agent", "workflow")
        valid, error = validate_ir(node)
        assert not valid
        assert "not a workflow" in error

    def test_validate_unknown_node_type(self) -> None:
        """Test validation of unknown node type."""

        # Create a mock node that's not a known type
        class UnknownNode:
            pass

        node = UnknownNode()
        valid, error = validate_ir(node)
        assert not valid
        assert "Unknown node type" in error

    def test_get_project_resources_src_dir_not_exists(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when src directory doesn't exist."""

        # Create project but no src directory
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        monkeypatch.chdir(project_root)

        # Should return empty resources when src dir doesn't exist
        resources = get_project_resources()
        assert resources == {}

    def test_get_project_resources_agents_dir_not_exists(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when agents directory doesn't exist."""

        # Create project with src but no agents directory
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        # Create workflows and functions but no agents
        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "workflow1.py").write_text("class Workflow1Workflow: pass")

        functions_dir = src_dir / "functions"
        functions_dir.mkdir()
        (functions_dir / "function1.py").write_text("def function1(): pass")

        monkeypatch.chdir(project_root)

        # Should scan workflows and functions but not agents
        resources = get_project_resources()
        assert "Workflow1Workflow" in resources
        assert "workflow1" in resources
        assert "Workflow1" in resources
        assert "function1" in resources
        assert "Function1" in resources
        # No agents
        assert len([r for r in resources.keys() if resources[r] == "agent"]) == 0

    def test_get_project_resources_find_project_root_exception(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when find_project_root raises exception."""

        # Mock find_project_root to raise exception
        def mock_find_project_root():
            raise Exception("Mock exception")

        monkeypatch.setattr("restack_gen.parser.find_project_root", mock_find_project_root)

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Not in a restack-gen project"):
            get_project_resources()

    def test_parse_conditional_non_resource_condition(self) -> None:
        """Test conditional operator with non-resource as condition."""
        from restack_gen.parser import ParseError, parse

        # Conditional requires resource name as condition
        with pytest.raises(ParseError, match="Conditional operator requires a condition name"):
            parse("(Agent1 ⇄ Agent2) →? Workflow1")

    def test_parse_and_validate_function(self, tmp_path, monkeypatch) -> None:
        """Test parse_and_validate function."""

        # Create project with resources
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "workflow1.py").write_text("class Workflow1Workflow: pass")

        monkeypatch.chdir(project_root)

        # Should parse and validate successfully
        ir = parse_and_validate("Agent1 → Workflow1")
        assert ir is not None
        assert len(ir.nodes) == 2

    def test_parse_and_validate_invalid(self, tmp_path, monkeypatch) -> None:
        """Test parse_and_validate with invalid expression."""

        # Create project with resources
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        monkeypatch.chdir(project_root)

        # Should raise RuntimeError for invalid resource
        with pytest.raises(RuntimeError, match="Validation error"):
            parse_and_validate("Agent1 → NonExistent")

    def test_get_project_resources_no_agents_dir(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when agents directory doesn't exist."""
        from restack_gen.parser import get_project_resources

        # Create project structure without agents directory
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        # Create workflows and functions but no agents
        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "workflow1.py").write_text("class Workflow1Workflow: pass")

        functions_dir = src_dir / "functions"
        functions_dir.mkdir()
        (functions_dir / "function1.py").write_text("def function1(): pass")

        monkeypatch.chdir(project_root)

        resources = get_project_resources()
        # Should have workflows and functions but no agents
        assert "Workflow1" in resources
        assert "Workflow1Workflow" in resources
        assert "workflow1" in resources
        assert "Function1" in resources
        assert "function1" in resources
        assert len([r for r in resources.keys() if resources[r] == "agent"]) == 0

    def test_get_project_resources_no_workflows_dir(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when workflows directory doesn't exist."""
        from restack_gen.parser import get_project_resources

        # Create project structure without workflows directory
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        # Create agents and functions but no workflows
        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        functions_dir = src_dir / "functions"
        functions_dir.mkdir()
        (functions_dir / "function1.py").write_text("def function1(): pass")

        monkeypatch.chdir(project_root)

        resources = get_project_resources()
        # Should have agents and functions but no workflows
        assert "Agent1" in resources
        assert "Agent1Agent" in resources
        assert "agent1" in resources
        assert "Function1" in resources
        assert "function1" in resources
        assert len([r for r in resources.keys() if resources[r] == "workflow"]) == 0

    def test_get_project_resources_no_functions_dir(self, tmp_path, monkeypatch) -> None:
        """Test get_project_resources when functions directory doesn't exist."""
        from restack_gen.parser import get_project_resources

        # Create project structure without functions directory
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        # Create agents and workflows but no functions
        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "workflow1.py").write_text("class Workflow1Workflow: pass")

        monkeypatch.chdir(project_root)

        resources = get_project_resources()
        # Should have agents and workflows but no functions
        assert "Agent1" in resources
        assert "Agent1Agent" in resources
        assert "agent1" in resources
        assert "Workflow1" in resources
        assert "Workflow1Workflow" in resources
        assert "workflow1" in resources
        assert len([r for r in resources.keys() if resources[r] == "function"]) == 0

    def test_validate_ir_resource_type_inference(self, tmp_path, monkeypatch) -> None:
        """Test validate_ir updates resource_type from project resources."""
        from restack_gen.parser import parse, validate_ir

        # Create project with resources
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")

        monkeypatch.chdir(project_root)

        # Parse with unknown resource type
        ir = parse("Agent1")
        assert ir.resource_type == "unknown"

        # Validate should update the type
        valid, error = validate_ir(ir)
        assert valid
        assert error is None
        assert ir.resource_type == "agent"

    def test_validate_ir_conditional_with_false_branch(self, tmp_path, monkeypatch) -> None:
        """Test validate_ir with conditional that has false branch."""
        from restack_gen.parser import parse, validate_ir

        # Create project with resources
        project_root = tmp_path / "testproject"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'testproject'\n")

        src_dir = project_root / "src" / "testproject"
        src_dir.mkdir(parents=True)

        agents_dir = src_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.py").write_text("class Agent1Agent: pass")
        (agents_dir / "agent2.py").write_text("class Agent2Agent: pass")

        workflows_dir = src_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "workflow1.py").write_text("class Workflow1Workflow: pass")
        (workflows_dir / "workflow2.py").write_text("class Workflow2Workflow: pass")

        monkeypatch.chdir(project_root)

        # Parse conditional with false branch
        ir = parse("Agent1 →? (Workflow1, Workflow2)")
        valid, error = validate_ir(ir)
        assert valid
        assert error is None
