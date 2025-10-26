"""Tests for pipeline validator."""

from restack_gen.ir import Conditional, Parallel, Resource, Sequence
from restack_gen.validator import PipelineValidator, validate_pipeline


class TestValidatorResourceCollection:
    """Tests for resource collection."""

    def test_collect_single_resource(self):
        """Test collecting resources from single resource."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Agent1"}

    def test_collect_sequence_resources(self):
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

    def test_collect_parallel_resources(self):
        """Test collecting resources from parallel branches."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Agent1", "Agent2"}

    def test_collect_conditional_resources(self):
        """Test collecting resources from conditional."""
        node = Conditional(
            condition="result['type']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        assert validator.all_resources == {"Handler1", "Handler2"}

    def test_collect_nested_resources(self):
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
    """Tests for cycle detection."""

    def test_no_cycle_single_resource(self):
        """Test that single resource has no cycle."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_simple_sequence(self):
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

    def test_no_cycle_parallel(self):
        """Test that parallel branches have no cycle."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_conditional(self):
        """Test that conditional has no cycle."""
        node = Conditional(
            condition="result['status']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        validator._check_cycles()  # Should not raise

    def test_no_cycle_complex_pipeline(self):
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
    """Tests for unreachable node detection."""

    def test_no_unreachable_single_resource(self):
        """Test single resource is reachable."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise

    def test_no_unreachable_sequence(self):
        """Test all sequence nodes are reachable."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise

    def test_no_unreachable_parallel(self):
        """Test all parallel branches are reachable."""
        node = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise

    def test_no_unreachable_conditional(self):
        """Test all conditional branches are reachable."""
        node = Conditional(
            condition="result['valid']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        validator._check_unreachable_nodes()  # Should not raise


class TestExecutionOrder:
    """Tests for execution order analysis."""

    def test_execution_order_sequence(self):
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

    def test_execution_order_parallel(self):
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

    def test_execution_order_conditional(self):
        """Test execution order includes all conditional paths."""
        node = Conditional(
            condition="result['route']",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        validator = PipelineValidator(node)
        order = validator.get_execution_order()
        assert set(order) == {"Handler1", "Handler2"}

    def test_execution_order_complex(self):
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
    """Tests for dependency analysis."""

    def test_dependencies_single_resource(self):
        """Test dependencies for single resource."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        deps = validator.get_dependencies()
        assert deps == {"Agent1": []}

    def test_dependencies_sequence(self):
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

    def test_dependencies_parallel(self):
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

    def test_dependencies_after_parallel(self):
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
    """Tests for graph metrics calculation."""

    def test_metrics_single_resource(self):
        """Test metrics for single resource."""
        node = Resource("Agent1", "agent")
        validator = PipelineValidator(node)
        metrics = validator.get_graph_metrics()
        assert metrics["total_resources"] == 1
        assert metrics["max_depth"] == 0
        assert metrics["parallel_sections"] == 0
        assert metrics["conditional_branches"] == 0

    def test_metrics_simple_sequence(self):
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

    def test_metrics_parallel(self):
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

    def test_metrics_conditional(self):
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

    def test_metrics_complex(self):
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
    """Tests for validate_pipeline convenience function."""

    def test_validate_valid_pipeline(self):
        """Test validation passes for valid pipeline."""
        node = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        validate_pipeline(node)  # Should not raise

    def test_validate_complex_pipeline(self):
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
