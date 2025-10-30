"""Tests for pipeline validator."""

import pytest

from restack_gen.ir import Conditional, Parallel, Resource, Sequence
from restack_gen.validator import PipelineValidator, ValidationError, validate_pipeline


class TestValidatorResourceCollection:
    def test_collect_unknown_node_type(self) -> None:
        """Test _collect_resources with an unknown node type (should do nothing)."""

        class DummyNode:
            pass

        node = DummyNode()
        validator = PipelineValidator(Resource("A", "agent"))
        # Should not raise
        validator._collect_resources(node)

    """Tests for resource collection."""

    def test_collect_single_resource(self) -> None:
        """Test collecting resources from single resource."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Agent1"}

    def test_collect_sequence_resources(self) -> None:
        """Test collecting resources from sequence."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Workflow1", "workflow"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Agent1", "Workflow1", "Agent2"}

    def test_collect_parallel_resources(self) -> None:
        """Test collecting resources from parallel branches."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Agent1", "Agent2"}

    def test_collect_conditional_resources(self) -> None:
        """Test collecting resources from conditional."""
        node = Conditional(
            condition="result['type']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Handler1", "Handler2"}

    def test_collect_nested_resources(self) -> None:
        pass

    def test_collect_conditional_no_false_branch(self) -> None:
        """Test collecting resources from a conditional with no false branch."""
        node = Conditional(condition="x", true_branch=Resource("A", "agent"), false_branch=None)
        validator = PipelineValidator(node)
        assert validator.all_resources == {"A"}
        """Test collecting resources from complex nested structure."""
        node = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Resource("Parallel1", "agent"),
                        Resource("Parallel2", "agent"),
                    ]
                ),
                Conditional(
                    condition="result['route']",
                    true_branch=Resource("TrueHandler", "agent"),
                    false_branch=Resource("FalseHandler", "agent"),
                ),
                Resource("End", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        assert validator.all_resources == {
            "Start",
            "Parallel1",
            "Parallel2",
            "TrueHandler",
            "FalseHandler",
            "End",
        }


class TestCycleDetection:
    def test_check_cycles_unknown_node_type(self) -> None:
        """Test _check_cycles with an unknown node type (should not raise)."""

        class DummyNode:
            pass

        validator = PipelineValidator(Resource("A", "agent"))
        # Patch root to dummy node
        validator.root = DummyNode()
        validator._check_cycles()  # Should not raise

    """Tests for cycle detection."""

    def test_no_cycle_single_resource(self) -> None:
        """Test that single resource has no cycle."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_simple_sequence(self) -> None:
        """Test that simple sequence has no cycle."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
                Resource("Agent3", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_parallel(self) -> None:
        """Test that parallel branches have no cycle."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_conditional(self) -> None:
        """Test that conditional has no cycle."""
        node = Conditional(
            condition="result['status']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_complex_pipeline(self) -> None:
        pass
        """Test that complex pipeline has no cycle."""
        node = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Resource("P1", "agent"),
                        Resource("P2", "agent"),
                    ]
                ),
                Conditional(
                    condition="result['branch']",
                    true_branch=Resource("T", "agent"),
                    false_branch=Resource("F", "agent"),
                ),
                Resource("End", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise


class TestUnreachableNodes:
    def test_mark_reachable_unknown_node_type(self) -> None:
        """Test mark_reachable with an unknown node type (should raise ValidationError for unreachable resource)."""

        class DummyNode:
            pass

        validator = PipelineValidator(Resource("A", "agent"))
        # Patch root to dummy node
        validator.root = DummyNode()
        with pytest.raises(ValidationError) as excinfo:
            validator._check_unreachable_nodes()
        assert "Unreachable nodes detected: A" in str(excinfo.value)

    """Tests for unreachable node detection."""

    def test_no_unreachable_single_resource(self) -> None:
        """Test single resource is reachable."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise

    def test_no_unreachable_sequence(self) -> None:
        """Test all sequence nodes are reachable."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise

    def test_no_unreachable_parallel(self) -> None:
        """Test all parallel branches are reachable."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise

    def test_no_unreachable_conditional(self) -> None:
        pass
        """Test all conditional branches are reachable."""
        node = Conditional(
            condition="result['valid']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise


class TestExecutionOrder:
    def test_traverse_unknown_node_type(self) -> None:
        """Test traverse with an unknown node type (should do nothing)."""

        class DummyNode:
            pass

        validator = PipelineValidator(Resource("A", "agent"))
        validator.root = DummyNode()
        order = validator.get_execution_order()
        assert order == []

    """Tests for execution order analysis."""

    def test_execution_order_sequence(self) -> None:
        """Test execution order for sequence."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
                Resource("Agent3", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        order = validator.get_execution_order()
        assert order == ["Agent1", "Agent2", "Agent3"]

    def test_execution_order_parallel(self) -> None:
        """Test execution order includes all parallel branches."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        order = validator.get_execution_order()
        assert set(order) == {"Agent1", "Agent2"}

    def test_execution_order_conditional(self) -> None:
        """Test execution order includes all conditional paths."""
        node = Conditional(
            condition="result['route']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        order = validator.get_execution_order()
        assert set(order) == {"Handler1", "Handler2"}

    def test_execution_order_complex(self) -> None:
        pass
        """Test execution order for complex pipeline."""
        node = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Resource("P1", "agent"),
                        Resource("P2", "agent"),
                    ]
                ),
                Resource("End", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        order = validator.get_execution_order()
        assert order[0] == "Start"
        assert order[-1] == "End"
        assert "P1" in order and "P2" in order


class TestDependencies:
    def test_build_deps_unknown_node_type(self) -> None:
        """Test build_deps with an unknown node type (should do nothing)."""

        class DummyNode:
            pass

        validator = PipelineValidator(Resource("A", "agent"))
        validator.root = DummyNode()
        deps = validator.get_dependencies()
        # Only the original resource should be present
        assert "A" in deps

    """Tests for dependency analysis."""

    def test_dependencies_single_resource(self) -> None:
        """Test dependencies for single resource."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        deps = validator.get_dependencies()
        assert deps == {"Agent1": []}

    def test_dependencies_sequence(self) -> None:
        """Test dependencies in sequence."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
                Resource("Agent3", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        deps = validator.get_dependencies()
        assert deps["Agent1"] == []
        assert deps["Agent2"] == ["Agent1"]
        assert deps["Agent3"] == ["Agent1", "Agent2"]

    def test_dependencies_parallel(self) -> None:
        """Test dependencies in parallel branches."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        deps = validator.get_dependencies()
        # Parallel branches have same predecessors (none in this case)
        assert deps["Agent1"] == []
        assert deps["Agent2"] == []

    def test_dependencies_after_parallel(self) -> None:
        pass
        """Test dependencies after parallel section."""
        node = Sequence(
            [
                Parallel(
                    [
                        Resource("P1", "agent"),
                        Resource("P2", "agent"),
                    ]
                ),
                Resource("After", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        deps = validator.get_dependencies()
        # After should depend on parallel branches completing
        assert deps["P1"] == []
        assert deps["P2"] == []


class TestGraphMetrics:
    def test_analyze_unknown_node_type(self) -> None:
        """Test analyze with an unknown node type (should do nothing)."""

        class DummyNode:
            pass

        validator = PipelineValidator(Resource("A", "agent"))
        validator.root = DummyNode()
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 1

    """Tests for graph metrics calculation."""

    def test_metrics_single_resource(self) -> None:
        """Test metrics for single resource."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 1
        assert metrics["max_depth"] == 0
        assert metrics["parallel_sections"] == 0
        assert metrics["conditional_branches"] == 0

    def test_metrics_simple_sequence(self) -> None:
        """Test metrics for simple sequence."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 2
        assert metrics["parallel_sections"] == 0
        assert metrics["conditional_branches"] == 0

    def test_metrics_parallel(self) -> None:
        """Test metrics with parallel sections."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 2
        assert metrics["parallel_sections"] == 1

    def test_metrics_conditional(self) -> None:
        """Test metrics with conditional branches."""
        node = Conditional(
            condition="result['type']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 2
        assert metrics["conditional_branches"] == 1

    def test_metrics_complex(self) -> None:
        pass
        """Test metrics for complex pipeline."""
        node = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Resource("P1", "agent"),
                        Resource("P2", "agent"),
                    ]
                ),
                Conditional(
                    condition="result['route']",
                    true_branch=Resource("T", "agent"),
                    false_branch=Resource("F", "agent"),
                ),
                Resource("End", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 6
        assert metrics["parallel_sections"] == 1
        assert metrics["conditional_branches"] == 1


class TestValidateFunction:
    def test_validate_pipeline_strict_mode_promotes_warnings(self) -> None:
        """Test that warnings are promoted to errors in strict mode."""
        # Create a pipeline that triggers a depth warning (depth > 5)
        node = Sequence(
            [
                Sequence(
                    [
                        Sequence(
                            [
                                Sequence(
                                    [
                                        Sequence(
                                            [
                                                Sequence(
                                                    [
                                                        Resource("A", "agent"),
                                                        Resource("B", "agent"),
                                                    ]
                                                ),
                                                Resource("C", "agent"),
                                            ]
                                        ),
                                        Resource("D", "agent"),
                                    ]
                                ),
                                Resource("E", "agent"),
                            ]
                        ),
                        Resource("F", "agent"),
                    ]
                ),
                Resource("G", "agent"),
            ]
        )
        result = validate_pipeline(node, strict=True)
        assert not result.is_valid
        assert any("Strict mode" in e for e in result.errors)

    """Tests for validate_pipeline convenience function."""

    def test_validate_valid_pipeline(self) -> None:
        """Test validation passes for valid pipeline."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validate_pipeline(node)  # Should not raise

    def test_validate_complex_pipeline(self) -> None:
        pass
        """Test validation for complex valid pipeline."""
        node = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Resource("P1", "agent"),
                        Resource("P2", "agent"),
                    ]
                ),
                Conditional(
                    condition="result['path']",
                    true_branch=Resource("T", "agent"),
                    false_branch=Resource("F", "agent"),
                ),
                Resource("End", "agent"),
            ]
        )
        validate_pipeline(node)  # Should not raise


def test_validation_error_message() -> None:
    """Test ValidationError can be created with custom message."""
    from restack_gen.validator import ValidationError

    error = ValidationError("Test error message")
    assert str(error) == "Test error message"
    assert isinstance(error, Exception)


def test_validation_result_creation() -> None:
    """Test creating ValidationResult objects."""
    from restack_gen.validator import ValidationResult

    result = ValidationResult(
        is_valid=True, errors=[], warnings=["Test warning"], stats={"depth": 3}
    )
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 1
    assert result.stats["depth"] == 3


def test_validation_result_with_errors() -> None:
    """Test ValidationResult with errors."""
    from restack_gen.validator import ValidationResult

    result = ValidationResult(
        is_valid=False,
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"],
        stats={"depth": 2},
    )
    assert result.is_valid is False
    assert len(result.errors) == 2
    assert len(result.warnings) == 1


def test_get_dependencies_single_resource() -> None:
    """Test getting dependencies for single resource."""
    node = Resource("Agent1", "agent")
    validator = PipelineValidator(node)
    deps = validator.get_dependencies()
    assert "Agent1" in deps
    assert deps["Agent1"] == []


def test_get_dependencies_sequence() -> None:
    """Test getting dependencies for sequence."""
    node = Sequence(
        [
            Resource("Agent1", "agent"),
            Resource("Agent2", "agent"),
            Resource("Agent3", "agent"),
        ]
    )
    validator = PipelineValidator(node)
    deps = validator.get_dependencies()
    assert deps["Agent1"] == []
    assert deps["Agent2"] == ["Agent1"]
    assert "Agent1" in deps["Agent3"] or "Agent2" in deps["Agent3"]


def test_get_dependencies_parallel() -> None:
    """Test getting dependencies for parallel branches."""
    node = Parallel([Resource("Agent1", "agent"), Resource("Agent2", "agent")])
    validator = PipelineValidator(node)
    deps = validator.get_dependencies()
    # Parallel branches should have same dependencies
    assert deps["Agent1"] == []
    assert deps["Agent2"] == []


def test_get_dependencies_conditional() -> None:
    """Test getting dependencies for conditional."""
    node = Conditional(
        condition="result['status']",
        true_branch=Resource("Handler1", "agent"),
        false_branch=Resource("Handler2", "agent"),
    )
    validator = PipelineValidator(node)
    deps = validator.get_dependencies()
    # Both branches should have same dependencies
    assert deps["Handler1"] == []
    assert deps["Handler2"] == []


def test_get_execution_order_single() -> None:
    """Test execution order for single resource."""
    node = Resource("Agent1", "agent")
    validator = PipelineValidator(node)
    order = validator.get_execution_order()
    assert order == ["Agent1"]


def test_get_execution_order_sequence() -> None:
    """Test execution order for sequence."""
    node = Sequence(
        [Resource("Agent1", "agent"), Resource("Agent2", "agent"), Resource("Agent3", "agent")]
    )
    validator = PipelineValidator(node)
    order = validator.get_execution_order()
    assert order == ["Agent1", "Agent2", "Agent3"]


def test_get_execution_order_parallel() -> None:
    """Test execution order for parallel branches."""
    node = Parallel([Resource("Agent1", "agent"), Resource("Agent2", "agent")])
    validator = PipelineValidator(node)
    order = validator.get_execution_order()
    # Both should be in order, exact order may vary
    assert set(order) == {"Agent1", "Agent2"}
    assert len(order) == 2


def test_get_execution_order_conditional() -> None:
    """Test execution order for conditional."""
    node = Conditional(
        condition="result['status']",
        true_branch=Resource("Handler1", "agent"),
        false_branch=Resource("Handler2", "agent"),
    )
    validator = PipelineValidator(node)
    order = validator.get_execution_order()
    # Both branches should be in order
    assert set(order) == {"Handler1", "Handler2"}


def test_validator_with_empty_sequence() -> None:
    """Test validator with sequence that has minimum nodes."""
    # Sequences require at least 2 nodes
    node = Sequence([Resource("A", "agent"), Resource("B", "agent")])
    validator = PipelineValidator(node)
    assert validator.all_resources == {"A", "B"}
    validator.validate()  # Should not raise


def test_validator_with_conditional_no_false_branch() -> None:
    """Test validator with conditional that has no false branch."""
    node = Conditional(
        condition="result['proceed']", true_branch=Resource("Handler", "agent"), false_branch=None
    )
    validator = PipelineValidator(node)
    assert validator.all_resources == {"Handler"}
    validator.validate()  # Should not raise


def test_collect_resources_deeply_nested() -> None:
    """Test collecting resources from deeply nested structure."""
    node = Sequence(
        [
            Sequence(
                [
                    Resource("A", "agent"),
                    Parallel([Resource("B", "agent"), Resource("C", "agent")]),
                ]
            ),
            Conditional(
                condition="x",
                true_branch=Sequence([Resource("D", "agent"), Resource("E", "agent")]),
                false_branch=Resource("F", "agent"),
            ),
        ]
    )
    validator = PipelineValidator(node)
    assert validator.all_resources == {"A", "B", "C", "D", "E", "F"}


def test_graph_metrics_with_types() -> None:
    """Test graph metrics includes resource types."""
    node = Sequence(
        [
            Resource("Agent1", "agent"),
            Resource("Workflow1", "workflow"),
            Resource("Func1", "function"),
        ]
    )
    validator = PipelineValidator(node)
    metrics = validator.get_graph_metrics()
    assert metrics["total_resources"] == 3


class TestValidationErrorPaths:
    """Tests for validation error conditions that raise exceptions."""

    def test_unreachable_nodes_error(self) -> None:
        """Test that unreachable nodes trigger ValidationError."""
        # Create a validator with a resource in all_resources that isn't in the tree
        # This simulates a parsing error or manual construction issue
        node = Resource("A", "agent")
        validator = PipelineValidator(node)

        # Manually add an unreachable resource to simulate error condition
        validator.all_resources.add("UnreachableAgent")

        with pytest.raises(ValidationError, match="Unreachable nodes detected"):
            validator._check_unreachable_nodes()

    def test_validate_function_with_depth_warning(self) -> None:
        """Test validation function with pipeline that triggers depth warning."""
        # Create a deeply nested sequence (depth > 5) - need 6 levels
        node = Sequence(
            [
                Resource("A", "agent"),
                Sequence(
                    [
                        Resource("B", "agent"),
                        Sequence(
                            [
                                Resource("C", "agent"),
                                Sequence(
                                    [
                                        Resource("D", "agent"),
                                        Sequence(
                                            [
                                                Resource("E", "agent"),
                                                Sequence(
                                                    [
                                                        Resource("F", "agent"),
                                                        Resource("G", "agent"),
                                                    ]
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        )

        result = validate_pipeline(node)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("Pipeline depth is high" in w for w in result.warnings)
        assert result.stats["max_depth"] > 5

    def test_validate_function_with_many_resources_warning(self) -> None:
        """Test validation function with pipeline that has > 20 resources."""
        # Create a sequence with 21 resources
        resources = [Resource(f"Agent{i}", "agent") for i in range(21)]
        node = Sequence(resources)

        result = validate_pipeline(node)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("Pipeline uses many resources" in w for w in result.warnings)
        assert result.stats["total_resources"] == 21

    def test_validate_function_with_many_parallel_sections_warning(self) -> None:
        """Test validation function with > 10 parallel sections."""
        # Create a sequence with 11 parallel sections
        parallels = [
            Parallel([Resource(f"A{i}", "agent"), Resource(f"B{i}", "agent")]) for i in range(11)
        ]
        node = Sequence(parallels)

        result = validate_pipeline(node)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("Pipeline has many parallel sections" in w for w in result.warnings)
        assert result.stats["parallel_sections"] == 11

    def test_validate_function_with_many_conditionals_warning(self) -> None:
        """Test validation function with > 10 conditional branches."""
        # Create a sequence with 11 conditionals
        conditionals = [
            Conditional(
                condition=f"check_{i}",
                true_branch=Resource(f"T{i}", "agent"),
                false_branch=Resource(f"F{i}", "agent"),
            )
            for i in range(11)
        ]
        node = Sequence(conditionals)

        result = validate_pipeline(node)
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any("Pipeline has many conditional branches" in w for w in result.warnings)
        assert result.stats["conditional_branches"] == 11

    def test_validate_function_strict_mode_promotes_warnings(self) -> None:
        """Test that strict mode promotes warnings to errors."""
        # Create a pipeline with depth > 5 to trigger warning (need 6 levels)
        node = Sequence(
            [
                Resource("A", "agent"),
                Sequence(
                    [
                        Resource("B", "agent"),
                        Sequence(
                            [
                                Resource("C", "agent"),
                                Sequence(
                                    [
                                        Resource("D", "agent"),
                                        Sequence(
                                            [
                                                Resource("E", "agent"),
                                                Sequence(
                                                    [
                                                        Resource("F", "agent"),
                                                        Resource("G", "agent"),
                                                    ]
                                                ),
                                            ]
                                        ),
                                    ]
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        )

        # Non-strict mode: warnings don't affect validity
        result_normal = validate_pipeline(node, strict=False)
        assert result_normal.is_valid
        assert len(result_normal.warnings) > 0
        assert len(result_normal.errors) == 0

        # Strict mode: warnings become errors
        result_strict = validate_pipeline(node, strict=True)
        assert not result_strict.is_valid
        assert len(result_strict.errors) > 0
        assert any("Strict mode:" in e for e in result_strict.errors)

    def test_validate_function_with_unreachable_nodes_error(self) -> None:
        """Test that unreachable nodes cause validation to fail."""
        node = Resource("A", "agent")
        validator = PipelineValidator(node)

        # Manually add unreachable resource
        validator.all_resources.add("UnreachableAgent")

        # Test the error path directly through the validator
        with pytest.raises(ValidationError):
            validator._check_unreachable_nodes()
