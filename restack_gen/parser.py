"""Parser for pipeline operator expressions.

This module implements a tokenizer and recursive descent parser for
operator expressions using →, ⇄, and →? operators.

Grammar (EBNF):
    expression := sequence
    sequence := parallel ( ARROW parallel )*
    parallel := primary ( PARALLEL primary )*
    primary := NAME | LPAREN expression RPAREN

Operator Precedence (highest to lowest):
    1. Parentheses ()
    2. Parallel (⇄)
    3. Sequence (→)

Example:
    parse("Agent1 → Workflow1 ⇄ Agent2 → Function1")

    Returns:
    Sequence([
        Resource("Agent1", "agent"),
        Parallel([
            Resource("Workflow1", "workflow"),
            Resource("Agent2", "agent")
        ]),
        Resource("Function1", "function")
    ])
"""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from restack_gen.generator import find_project_root, get_project_name
from restack_gen.ir import (
    Conditional,
    IRNode,
    Parallel,
    Resource,
    Sequence,
    flatten_parallel,
    flatten_sequence,
)


class TokenType(Enum):
    """Token types for operator expressions."""

    NAME = auto()  # Resource name (e.g., Agent1, process_data)
    ARROW = auto()  # → (sequence operator)
    PARALLEL = auto()  # ⇄ (parallel operator)
    CONDITIONAL = auto()  # →? (conditional operator)
    COMMA = auto()  # , (used in conditional branches)
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    EOF = auto()  # End of input


@dataclass
class Token:
    """A token in the operator expression.

    Attributes:
        type: Type of token
        value: String value of token
        position: Character position in input (0-indexed)
    """

    type: TokenType
    value: str
    position: int

    def __str__(self) -> str:
        """Return readable string representation."""
        return f"Token({self.type.name}, '{self.value}', pos={self.position})"


class ParseError(Exception):
    """Error raised during parsing."""

    def __init__(self, message: str, position: int = -1):
        """Initialize parse error.

        Args:
            message: Error description
            position: Character position where error occurred
        """
        self.position = position
        super().__init__(message)


def tokenize(expression: str) -> list[Token]:
    """Tokenize an operator expression.

    Splits input into tokens, handling whitespace and operators.

    Args:
        expression: Operator expression string

    Returns:
        List of tokens (always ends with EOF token)

    Raises:
        ParseError: If input contains invalid characters

    Example:
        >>> tokens = tokenize("Agent1 → Workflow1")
        >>> [t.type.name for t in tokens]
        ['NAME', 'ARROW', 'NAME', 'EOF']
    """
    tokens = []
    position = 0
    length = len(expression)

    while position < length:
        char = expression[position]

        # Skip whitespace
        if char.isspace():
            position += 1
            continue

        # Check for operators (must check multi-char first)
        if expression[position : position + 2] == "→?":
            tokens.append(Token(TokenType.CONDITIONAL, "→?", position))
            position += 2
            continue

        if char == "→":
            tokens.append(Token(TokenType.ARROW, "→", position))
            position += 1
            continue

        if char == "⇄":
            tokens.append(Token(TokenType.PARALLEL, "⇄", position))
            position += 1
            continue

        if char == ",":
            tokens.append(Token(TokenType.COMMA, ",", position))
            position += 1
            continue

        # Parentheses
        if char == "(":
            tokens.append(Token(TokenType.LPAREN, "(", position))
            position += 1
            continue

        if char == ")":
            tokens.append(Token(TokenType.RPAREN, ")", position))
            position += 1
            continue

        # Resource name (alphanumeric + underscore)
        if char.isalnum() or char == "_":
            start_pos = position
            name_chars = []
            while position < length and (
                expression[position].isalnum() or expression[position] == "_"
            ):
                name_chars.append(expression[position])
                position += 1
            name = "".join(name_chars)
            tokens.append(Token(TokenType.NAME, name, start_pos))
            continue

        # Invalid character
        raise ParseError(f"Invalid character '{char}' at position {position}", position)

    # Add EOF token
    tokens.append(Token(TokenType.EOF, "", position))
    return tokens


class Parser:
    """Recursive descent parser for operator expressions."""

    def __init__(self, tokens: list[Token]):
        """Initialize parser.

        Args:
            tokens: List of tokens from tokenizer
        """
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else Token(TokenType.EOF, "", 0)

    def advance(self) -> None:
        """Move to next token."""
        if self.position < len(self.tokens) - 1:
            self.position += 1
            self.current_token = self.tokens[self.position]

    def expect(self, token_type: TokenType) -> Token:
        """Expect a specific token type and advance.

        Args:
            token_type: Expected token type

        Returns:
            The current token

        Raises:
            ParseError: If current token doesn't match expected type
        """
        if self.current_token.type != token_type:
            raise ParseError(
                f"Expected {token_type.name}, got {self.current_token.type.name} "
                f"at position {self.current_token.position}",
                self.current_token.position,
            )
        token = self.current_token
        self.advance()
        return token

    def parse_expression(self) -> IRNode:
        """Parse top-level expression.

        expression := sequence

        Returns:
            Root IR node
        """
        return self.parse_sequence()

    def parse_sequence(self) -> IRNode:
        """Parse sequence (lowest precedence).

        sequence := parallel ( ARROW parallel )*

        Returns:
            Sequence node or single parallel node
        """
        nodes = [self.parse_conditional()]

        while self.current_token.type == TokenType.ARROW:
            self.advance()  # consume →
            nodes.append(self.parse_conditional())

        if len(nodes) == 1:
            return nodes[0]
        return flatten_sequence(Sequence(nodes))

    def parse_conditional(self) -> IRNode:
        """Parse conditional expressions.

        conditional := parallel ( CONDITIONAL LPAREN expression ( COMMA expression )? RPAREN )*

        Returns:
            Either a plain parallel node or Conditional node
        """
        node = self.parse_parallel()

        while self.current_token.type == TokenType.CONDITIONAL:
            self.advance()  # consume →?

            # The left side must resolve to a simple resource name used as condition key
            if not isinstance(node, Resource):
                raise ParseError(
                    "Conditional operator requires a condition name before →?",
                    self.current_token.position,
                )

            condition_name = node.name

            self.expect(TokenType.LPAREN)
            true_branch = self.parse_expression()
            false_branch: IRNode | None = None

            # Capture current token type in a local variable to avoid over-narrowing in type checkers
            current_type = self.current_token.type
            if current_type == TokenType.COMMA:  # type: ignore[comparison-overlap]
                self.advance()  # consume ,
                false_branch = self.parse_expression()

            self.expect(TokenType.RPAREN)
            node = Conditional(condition_name, true_branch, false_branch)

        return node

    def parse_parallel(self) -> IRNode:
        """Parse parallel (higher precedence than sequence).

        parallel := primary ( PARALLEL primary )*

        Returns:
            Parallel node or single primary node
        """
        nodes = [self.parse_primary()]

        while self.current_token.type == TokenType.PARALLEL:
            self.advance()  # consume ⇄
            nodes.append(self.parse_primary())

        if len(nodes) == 1:
            return nodes[0]
        return flatten_parallel(Parallel(nodes))

    def parse_primary(self) -> IRNode:
        """Parse primary expression (highest precedence).

        primary := NAME | LPAREN expression RPAREN

        Returns:
            Resource node or grouped expression

        Raises:
            ParseError: If syntax is invalid
        """
        # Grouped expression
        if self.current_token.type == TokenType.LPAREN:
            self.advance()  # consume (
            node = self.parse_expression()
            self.expect(TokenType.RPAREN)  # consume )
            return node

        # Resource name
        if self.current_token.type == TokenType.NAME:
            name = self.current_token.value
            self.advance()
            # For now, we don't know the resource type - validation will determine it
            # Use placeholder "unknown" type - validator will fix this
            return Resource(name, "unknown")

        # Unexpected token
        raise ParseError(
            f"Unexpected token {self.current_token.type.name} "
            f"at position {self.current_token.position}",
            self.current_token.position,
        )


def parse(expression: str) -> IRNode:
    """Parse an operator expression into an IR tree.

    Args:
        expression: Operator expression string

    Returns:
        Root IR node of parsed tree

    Raises:
        ParseError: If syntax is invalid

    Example:
        >>> ir = parse("Agent1 → Workflow1 ⇄ Agent2")
        >>> isinstance(ir, Sequence)
        True
    """
    if not expression or not expression.strip():
        raise ParseError("Empty expression")

    tokens = tokenize(expression)
    parser = Parser(tokens)
    ir = parser.parse_expression()

    # Ensure we consumed all tokens (except EOF)
    if parser.current_token.type != TokenType.EOF:
        raise ParseError(
            f"Unexpected token {parser.current_token.type.name} "
            f"at position {parser.current_token.position}",
            parser.current_token.position,
        )

    return ir


def get_project_resources() -> dict[str, str]:
    """Get all resources in the current project.

    Returns:
        Dict mapping resource name to type ("agent", "workflow", "function")

    Raises:
        RuntimeError: If not in a project directory
    """
    try:
        project_root = find_project_root()
        if project_root is None:
            raise RuntimeError("Could not find pyproject.toml")
        project_name = get_project_name(project_root)
    except Exception as e:
        raise RuntimeError(f"Not in a restack-gen project: {e}") from None

    src_dir = project_root / "src" / project_name
    resources: dict[str, str] = {}

    def register(name: str, resource_type: str) -> None:
        """Register a resource name if not already present."""
        if not name:
            return
        resources.setdefault(name, resource_type)

    # Scan agents
    agents_dir = src_dir / "agents"
    if agents_dir.exists():
        for file in agents_dir.glob("*.py"):
            if file.name != "__init__.py":
                module_name = file.stem
                parts = module_name.split("_")
                base_name = "".join(p.capitalize() for p in parts)
                class_name = base_name + "Agent"
                # Support class name, base PascalCase, and snake_case references
                register(class_name, "agent")
                register(base_name, "agent")
                register(module_name, "agent")

    # Scan workflows
    workflows_dir = src_dir / "workflows"
    if workflows_dir.exists():
        for file in workflows_dir.glob("*.py"):
            if file.name != "__init__.py":
                module_name = file.stem
                parts = module_name.split("_")
                base_name = "".join(p.capitalize() for p in parts)
                class_name = base_name + "Workflow"
                register(class_name, "workflow")
                register(base_name, "workflow")
                register(module_name, "workflow")

    # Scan functions
    functions_dir = src_dir / "functions"
    if functions_dir.exists():
        for file in functions_dir.glob("*.py"):
            if file.name != "__init__.py":
                # Functions use snake_case names
                module_name = file.stem
                base_name = "".join(p.capitalize() for p in module_name.split("_"))
                register(module_name, "function")
                register(base_name, "function")

    return resources


def validate_ir(
    ir: IRNode, project_root: Path | None = None, resources: dict[str, str] | None = None
) -> tuple[bool, str | None]:
    """Validate an IR tree against the current project.

    Checks:
    1. All Resource names exist in the project
    2. Resource types are correctly identified
    3. No obviously invalid structures

    Args:
        ir: IR tree to validate
        project_root: Optional project root (defaults to current)

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None

    Example:
        >>> ir = parse("Agent1 → NonExistent")
        >>> valid, error = validate_ir(ir)
        >>> print(error)
        Resource 'NonExistent' not found in project
    """
    if resources is None:
        try:
            resources = get_project_resources()
        except RuntimeError as e:
            return False, str(e)

    def validate_node(node: IRNode) -> tuple[bool, str | None]:
        """Recursively validate a node."""
        if isinstance(node, Resource):
            # Check if resource exists
            if node.name not in resources:
                return False, f"Resource '{node.name}' not found in project"
            project_type = resources[node.name]
            # Always check for type mismatch if node.resource_type is set and not 'unknown'
            if node.resource_type != "unknown" and node.resource_type is not None:
                if project_type != node.resource_type:
                    return (
                        False,
                        f"Resource '{node.name}' is a {project_type}, "
                        f"not a {node.resource_type}",
                    )
            else:
                # If not set or unknown, update from project resources
                node.resource_type = project_type
            return True, None

        if isinstance(node, (Sequence, Parallel)):
            # Validate all child nodes
            for child in node.nodes:
                valid, error = validate_node(child)
                if not valid:
                    return False, error
            return True, None

        if isinstance(node, Conditional):
            # Validate both branches
            valid, error = validate_node(node.true_branch)
            if not valid:
                return False, error
            if node.false_branch:
                valid, error = validate_node(node.false_branch)
                if not valid:
                    return False, error
            return True, None

        return False, f"Unknown node type: {type(node).__name__}"

    return validate_node(ir)


def parse_and_validate(expression: str) -> IRNode:
    """Parse and validate an operator expression.

    Convenience function that both parses and validates the expression.

    Args:
        expression: Operator expression string

    Returns:
        Validated IR tree (with resource types filled in)

    Raises:
        ParseError: If syntax is invalid
        RuntimeError: If validation fails

    Example:
        >>> ir = parse_and_validate("DataAgent → ProcessWorkflow")
        >>> ir.nodes[0].resource_type
        'agent'
    """
    ir = parse(expression)
    valid, error = validate_ir(ir)
    if not valid:
        raise RuntimeError(f"Validation error: {error}")
    return ir
