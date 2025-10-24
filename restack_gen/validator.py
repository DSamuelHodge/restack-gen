"""
Pipeline validation utilities.

This module provides validation for pipeline IR structures, including:
- Cycle detection in workflow graphs
- Unreachable node detection
- Resource existence validation
- Graph analysis utilities
"""

from typing import Any

from restack_gen.ir import Conditional, IRNode, Parallel, Resource, Sequence


class ValidationError(Exception):
    """Exception raised when pipeline validation fails."""

    pass


class PipelineValidator:
    """Validator for pipeline IR structures."""

    def __init__(self, root: IRNode):
        """
        Initialize validator with pipeline root node.

        Args:
            root: Root node of the IR tree
        """
        self.root = root
        self.all_resources: set[str] = set()
        self._collect_resources(root)

    def _collect_resources(self, node: IRNode) -> None:
        """
        Recursively collect all resources in the IR tree.

        Args:
            node: Current node to process
        """
        if isinstance(node, Resource):
            self.all_resources.add(node.name)
        elif isinstance(node, Sequence):
            for child in node.nodes:
                self._collect_resources(child)
        elif isinstance(node, Parallel):
            for child in node.nodes:
                self._collect_resources(child)
        elif isinstance(node, Conditional):
            self._collect_resources(node.true_branch)
            if node.false_branch:
                self._collect_resources(node.false_branch)

    def validate(self) -> None:
        """
        Validate the complete pipeline.

        Raises:
            ValidationError: If validation fails
        """
        self._check_cycles()
        self._check_unreachable_nodes()

    def _check_cycles(self) -> None:
        """
        Check for cycles in the workflow graph.

        Raises:
            ValidationError: If a cycle is detected
        """
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: IRNode, path: list[str]) -> bool:
            """
            DFS-based cycle detection.

            Args:
                node: Current node being visited
                path: Current path of resource names

            Returns:
                True if cycle detected, False otherwise
            """
            if isinstance(node, Resource):
                if node.name in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(node.name)
                    cycle_path = " → ".join(path[cycle_start:] + [node.name])
                    raise ValidationError(f"Cycle detected: {cycle_path}")

                if node.name in visited:
                    return False

                visited.add(node.name)
                rec_stack.add(node.name)
                # No children for Resource nodes in current implementation
                rec_stack.remove(node.name)
                return False

            elif isinstance(node, Sequence):
                for child in node.nodes:
                    if has_cycle(child, path):
                        return True

            elif isinstance(node, Parallel):
                for child in node.nodes:
                    if has_cycle(child, path):
                        return True

            elif isinstance(node, Conditional):
                if has_cycle(node.true_branch, path):
                    return True
                if node.false_branch and has_cycle(node.false_branch, path):
                    return True

            return False

        has_cycle(self.root, [])

    def _check_unreachable_nodes(self) -> None:
        """
        Check for unreachable nodes in the pipeline.

        In a well-formed pipeline, all resources should be reachable from the root.
        This is primarily a sanity check since our IR construction ensures connectivity.

        Raises:
            ValidationError: If unreachable nodes are found
        """
        reachable: set[str] = set()

        def mark_reachable(node: IRNode) -> None:
            """
            Mark all reachable resources.

            Args:
                node: Current node being processed
            """
            if isinstance(node, Resource):
                reachable.add(node.name)
            elif isinstance(node, Sequence):
                for child in node.nodes:
                    mark_reachable(child)
            elif isinstance(node, Parallel):
                for child in node.nodes:
                    mark_reachable(child)
            elif isinstance(node, Conditional):
                mark_reachable(node.true_branch)
                if node.false_branch:
                    mark_reachable(node.false_branch)

        mark_reachable(self.root)

        unreachable = self.all_resources - reachable
        if unreachable:
            raise ValidationError(
                f"Unreachable nodes detected: {', '.join(sorted(unreachable))}"
            )

    def get_execution_order(self) -> list[str]:
        """
        Get a possible execution order of resources (topological sort).

        Returns:
            List of resource names in execution order
        """
        order: list[str] = []

        def traverse(node: IRNode) -> None:
            """
            Traverse IR tree in execution order.

            Args:
                node: Current node to process
            """
            if isinstance(node, Resource):
                if node.name not in order:
                    order.append(node.name)
            elif isinstance(node, Sequence):
                for child in node.nodes:
                    traverse(child)
            elif isinstance(node, Parallel):
                # Parallel branches can execute in any order
                for child in node.nodes:
                    traverse(child)
            elif isinstance(node, Conditional):
                # Both branches are possible execution paths
                traverse(node.true_branch)
                if node.false_branch:
                    traverse(node.false_branch)

        traverse(self.root)
        return order

    def get_dependencies(self) -> dict[str, list[str]]:
        """
        Get dependency graph: for each resource, list of resources it depends on.

        Returns:
            Dictionary mapping resource names to their dependencies
        """
        dependencies: dict[str, list[str]] = {name: [] for name in self.all_resources}

        def build_deps(node: IRNode, predecessors: list[str]) -> None:
            """
            Build dependency relationships.

            Args:
                node: Current node
                predecessors: List of resources that must execute before this node
            """
            if isinstance(node, Resource):
                dependencies[node.name].extend(predecessors)
            elif isinstance(node, Sequence):
                current_preds = list(predecessors)
                for child in node.nodes:
                    build_deps(child, current_preds)
                    # For sequences, each step depends on previous steps
                    if isinstance(child, Resource):
                        current_preds.append(child.name)
            elif isinstance(node, Parallel):
                # All parallel branches start with same predecessors
                for child in node.nodes:
                    build_deps(child, predecessors)
            elif isinstance(node, Conditional):
                build_deps(node.true_branch, next_preds)
                # Both branches depend on predecessors
                build_deps(node.true_branch, predecessors)
                if node.false_branch:
                    build_deps(node.false_branch, predecessors)

        build_deps(self.root, [])
        return dependencies

    def get_graph_metrics(self) -> dict[str, Any]:
        """
        Calculate graph metrics for the pipeline.

        Returns:
            Dictionary containing:
            - total_resources: Number of unique resources
            - max_depth: Maximum depth of the pipeline
            - parallel_sections: Number of parallel execution sections
            - conditional_branches: Number of conditional branches
        """
        metrics = {
            "total_resources": len(self.all_resources),
            "max_depth": 0,
            "parallel_sections": 0,
            "conditional_branches": 0,
        }

        def analyze(node: IRNode, depth: int) -> None:
            """
            Analyze node and update metrics.

            Args:
                node: Current node
                depth: Current depth in tree
            """
            metrics["max_depth"] = max(metrics["max_depth"], depth)

            if isinstance(node, Parallel):
                metrics["parallel_sections"] += 1
                for child in node.nodes:
                    analyze(child, depth + 1)
            elif isinstance(node, Conditional):
                metrics["conditional_branches"] += 1
                analyze(node.true_branch, depth + 1)
                if node.false_branch:
                    analyze(node.false_branch, depth + 1)
            elif isinstance(node, Sequence):
                for child in node.nodes:
                    analyze(child, depth + 1)

        analyze(self.root, 0)
        return metrics


def validate_pipeline(root: IRNode) -> None:
    """
    Validate a pipeline IR structure.

    Convenience function that creates a validator and runs validation.

    Args:
        root: Root node of the IR tree

    Raises:
        ValidationError: If validation fails
    """
    validator = PipelineValidator(root)
    validator.validate()
