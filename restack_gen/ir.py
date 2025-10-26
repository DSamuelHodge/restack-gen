"""Intermediate Representation (IR) for pipeline expressions.

This module defines the IR nodes used to represent parsed operator expressions.
The IR serves as an intermediate step between parsing and code generation.

Operator Syntax:
- → (sequence): Execute nodes in order
- ⇄ (parallel): Execute nodes concurrently
- →? (conditional): Branch based on condition

Example:
    Agent1 → Workflow1 ⇄ Agent2 → Function1

    Parses to:
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
from typing import overload


@dataclass
class IRNode:
    """Base class for all IR nodes."""

    def __str__(self) -> str:
        """Return string representation for debugging."""
        return self.__repr__()


@dataclass
class Resource(IRNode):
    """Reference to a resource (agent, workflow, or function).

    Attributes:
        name: The name of the resource (e.g., "DataCollector", "process_email")
        resource_type: Type of resource ("agent", "workflow", "function", or "unknown")
                      "unknown" is allowed during parsing and should be resolved during validation
    """

    name: str
    resource_type: str

    def __post_init__(self) -> None:
        """Validate resource type."""
        valid_types = {"agent", "workflow", "function", "unknown"}
        if self.resource_type not in valid_types:
            raise ValueError(
                f"Invalid resource type '{self.resource_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )

    def __str__(self) -> str:
        """Return readable string representation."""
        return f"{self.resource_type.capitalize()}({self.name})"


@dataclass
class Sequence(IRNode):
    """Sequential execution of nodes (→ operator).

    Nodes are executed in order, one after another.

    Attributes:
        nodes: List of IR nodes to execute sequentially
    """

    nodes: list[IRNode]

    def __post_init__(self) -> None:
        """Validate sequence has at least 2 nodes."""
        if len(self.nodes) < 2:
            raise ValueError(f"Sequence must have at least 2 nodes, got {len(self.nodes)}")

    def __str__(self) -> str:
        """Return readable string representation."""
        node_strs = [str(node) for node in self.nodes]
        return f"Sequence([{' → '.join(node_strs)}])"


@dataclass
class Parallel(IRNode):
    """Parallel execution of nodes (⇄ operator).

    All nodes are executed concurrently using asyncio.gather().

    Attributes:
        nodes: List of IR nodes to execute in parallel
    """

    nodes: list[IRNode]

    def __post_init__(self) -> None:
        """Validate parallel has at least 2 nodes."""
        if len(self.nodes) < 2:
            raise ValueError(f"Parallel must have at least 2 nodes, got {len(self.nodes)}")

    def __str__(self) -> str:
        """Return readable string representation."""
        node_strs = [str(node) for node in self.nodes]
        return f"Parallel([{' ⇄ '.join(node_strs)}])"


@dataclass
class Conditional(IRNode):
    """Conditional execution (→? operator).

    Executes one of two branches based on a condition evaluated at runtime.

    Attributes:
        condition: Condition expression (evaluated from previous result)
        true_branch: IR node to execute if condition is true
        false_branch: IR node to execute if condition is false (optional)
    """

    condition: str
    true_branch: IRNode
    false_branch: IRNode | None = None

    def __post_init__(self) -> None:
        """Validate condition is not empty."""
        if not self.condition or not self.condition.strip():
            raise ValueError("Conditional condition cannot be empty")

    def __str__(self) -> str:
        """Return readable string representation."""
        if self.false_branch:
            return f"Conditional({self.condition} ? {self.true_branch} : {self.false_branch})"
        return f"Conditional({self.condition} ? {self.true_branch})"


@overload
def flatten_sequence(node: Sequence) -> Sequence:  # noqa: D401 - overload docs inherited
    ...


@overload
def flatten_sequence(node: IRNode) -> IRNode:  # noqa: D401 - overload docs inherited
    ...


def flatten_sequence(node: IRNode) -> IRNode:
    """Flatten nested sequences into a single sequence.

    Transforms: Sequence([A, Sequence([B, C]), D])
    Into: Sequence([A, B, C, D])

    Args:
        node: IR node to flatten

    Returns:
        Flattened IR node (sequences merged, other nodes unchanged)
    """
    if not isinstance(node, Sequence):
        return node

    flattened_nodes: list[IRNode] = []
    for child in node.nodes:
        if isinstance(child, Sequence):
            # Recursively flatten nested sequences
            # In this branch, child is Sequence, and overload ensures return type is Sequence
            flattened_child = flatten_sequence(child)
            flattened_nodes.extend(flattened_child.nodes)
        else:
            flattened_nodes.append(child)

    return Sequence(flattened_nodes)


@overload
def flatten_parallel(node: Parallel) -> Parallel:  # noqa: D401 - overload docs inherited
    ...


@overload
def flatten_parallel(node: IRNode) -> IRNode:  # noqa: D401 - overload docs inherited
    ...


def flatten_parallel(node: IRNode) -> IRNode:
    """Flatten nested parallel nodes into a single parallel node.

    Transforms: Parallel([A, Parallel([B, C]), D])
    Into: Parallel([A, B, C, D])

    Args:
        node: IR node to flatten

    Returns:
        Flattened IR node (parallel merged, other nodes unchanged)
    """
    if not isinstance(node, Parallel):
        return node

    flattened_nodes: list[IRNode] = []
    for child in node.nodes:
        if isinstance(child, Parallel):
            # Recursively flatten nested parallel
            # In this branch, child is Parallel, and overload ensures return type is Parallel
            flattened_child = flatten_parallel(child)
            flattened_nodes.extend(flattened_child.nodes)
        else:
            flattened_nodes.append(child)

    return Parallel(flattened_nodes)
