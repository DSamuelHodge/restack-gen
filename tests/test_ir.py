"""Tests for IR (Intermediate Representation) nodes."""

import pytest

from restack_gen.ir import (
    Conditional,
    Parallel,
    Resource,
    Sequence,
    flatten_parallel,
    flatten_sequence,
)


class TestResource:
    """Tests for Resource IR node."""

    def test_create_agent_resource(self):
        """Test creating an agent resource."""
        resource = Resource("DataCollector", "agent")
        assert resource.name == "DataCollector"
        assert resource.resource_type == "agent"

    def test_create_workflow_resource(self):
        """Test creating a workflow resource."""
        resource = Resource("ProcessEmail", "workflow")
        assert resource.name == "ProcessEmail"
        assert resource.resource_type == "workflow"

    def test_create_function_resource(self):
        """Test creating a function resource."""
        resource = Resource("transform_data", "function")
        assert resource.name == "transform_data"
        assert resource.resource_type == "function"

    def test_invalid_resource_type(self):
        """Test that invalid resource type raises error."""
        with pytest.raises(ValueError, match="Invalid resource type"):
            Resource("Test", "invalid")

    def test_resource_string_representation(self):
        """Test string representation of resource."""
        resource = Resource("TestAgent", "agent")
        assert str(resource) == "Agent(TestAgent)"

        resource = Resource("TestWorkflow", "workflow")
        assert str(resource) == "Workflow(TestWorkflow)"

        resource = Resource("test_function", "function")
        assert str(resource) == "Function(test_function)"

    def test_resource_equality(self):
        """Test resource equality comparison."""
        r1 = Resource("Test", "agent")
        r2 = Resource("Test", "agent")
        r3 = Resource("Other", "agent")
        r4 = Resource("Test", "workflow")

        assert r1 == r2
        assert r1 != r3
        assert r1 != r4


class TestSequence:
    """Tests for Sequence IR node."""

    def test_create_sequence(self):
        """Test creating a sequence node."""
        nodes = [
            Resource("Agent1", "agent"),
            Resource("Workflow1", "workflow"),
        ]
        seq = Sequence(nodes)
        assert len(seq.nodes) == 2
        assert seq.nodes[0].name == "Agent1"
        assert seq.nodes[1].name == "Workflow1"

    def test_sequence_requires_two_nodes(self):
        """Test that sequence requires at least 2 nodes."""
        with pytest.raises(ValueError, match="at least 2 nodes"):
            Sequence([Resource("Single", "agent")])

    def test_sequence_string_representation(self):
        """Test string representation of sequence."""
        seq = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Workflow1", "workflow"),
                Resource("Agent2", "agent"),
            ]
        )
        assert "Agent(Agent1) → Workflow(Workflow1) → Agent(Agent2)" in str(seq)

    def test_nested_sequence(self):
        """Test creating nested sequences."""
        inner = Sequence(
            [
                Resource("A", "agent"),
                Resource("B", "workflow"),
            ]
        )
        outer = Sequence(
            [
                Resource("Start", "agent"),
                inner,
            ]
        )
        assert len(outer.nodes) == 2
        assert isinstance(outer.nodes[1], Sequence)


class TestParallel:
    """Tests for Parallel IR node."""

    def test_create_parallel(self):
        """Test creating a parallel node."""
        nodes = [
            Resource("Agent1", "agent"),
            Resource("Agent2", "agent"),
        ]
        par = Parallel(nodes)
        assert len(par.nodes) == 2
        assert par.nodes[0].name == "Agent1"
        assert par.nodes[1].name == "Agent2"

    def test_parallel_requires_two_nodes(self):
        """Test that parallel requires at least 2 nodes."""
        with pytest.raises(ValueError, match="at least 2 nodes"):
            Parallel([Resource("Single", "agent")])

    def test_parallel_string_representation(self):
        """Test string representation of parallel."""
        par = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
                Resource("Agent3", "agent"),
            ]
        )
        assert "Agent(Agent1) ⇄ Agent(Agent2) ⇄ Agent(Agent3)" in str(par)

    def test_nested_parallel(self):
        """Test creating nested parallel nodes."""
        inner = Parallel(
            [
                Resource("A", "agent"),
                Resource("B", "agent"),
            ]
        )
        outer = Parallel(
            [
                Resource("Start", "agent"),
                inner,
            ]
        )
        assert len(outer.nodes) == 2
        assert isinstance(outer.nodes[1], Parallel)


class TestConditional:
    """Tests for Conditional IR node."""

    def test_create_conditional_with_both_branches(self):
        """Test creating conditional with true and false branches."""
        cond = Conditional(
            condition="result.success",
            true_branch=Resource("SuccessHandler", "agent"),
            false_branch=Resource("ErrorHandler", "agent"),
        )
        assert cond.condition == "result.success"
        assert cond.true_branch.name == "SuccessHandler"
        assert cond.false_branch.name == "ErrorHandler"

    def test_create_conditional_with_only_true_branch(self):
        """Test creating conditional with only true branch."""
        cond = Conditional(
            condition="result.success",
            true_branch=Resource("SuccessHandler", "agent"),
        )
        assert cond.condition == "result.success"
        assert cond.true_branch.name == "SuccessHandler"
        assert cond.false_branch is None

    def test_conditional_requires_non_empty_condition(self):
        """Test that conditional requires non-empty condition."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Conditional(
                condition="",
                true_branch=Resource("Handler", "agent"),
            )

        with pytest.raises(ValueError, match="cannot be empty"):
            Conditional(
                condition="   ",
                true_branch=Resource("Handler", "agent"),
            )

    def test_conditional_string_representation_both_branches(self):
        """Test string representation with both branches."""
        cond = Conditional(
            condition="result.success",
            true_branch=Resource("Success", "agent"),
            false_branch=Resource("Error", "agent"),
        )
        result = str(cond)
        assert "result.success" in result
        assert "Success" in result
        assert "Error" in result

    def test_conditional_string_representation_one_branch(self):
        """Test string representation with only true branch."""
        cond = Conditional(
            condition="result.success",
            true_branch=Resource("Success", "agent"),
        )
        result = str(cond)
        assert "result.success" in result
        assert "Success" in result


class TestFlattenSequence:
    """Tests for flatten_sequence utility function."""

    def test_flatten_nested_sequences(self):
        """Test flattening nested sequences."""
        inner = Sequence(
            [
                Resource("B", "agent"),
                Resource("C", "workflow"),
            ]
        )
        outer = Sequence(
            [
                Resource("A", "agent"),
                inner,
                Resource("D", "function"),
            ]
        )

        flattened = flatten_sequence(outer)
        assert isinstance(flattened, Sequence)
        assert len(flattened.nodes) == 4
        assert all(isinstance(node, Resource) for node in flattened.nodes)
        assert [n.name for n in flattened.nodes] == ["A", "B", "C", "D"]

    def test_flatten_non_sequence_unchanged(self):
        """Test that non-sequence nodes are unchanged."""
        resource = Resource("Test", "agent")
        result = flatten_sequence(resource)
        assert result is resource

        parallel = Parallel(
            [
                Resource("A", "agent"),
                Resource("B", "agent"),
            ]
        )
        result = flatten_sequence(parallel)
        assert result is parallel

    def test_flatten_deeply_nested_sequences(self):
        """Test flattening deeply nested sequences."""
        level3 = Sequence(
            [
                Resource("C", "agent"),
                Resource("D", "agent"),
            ]
        )
        level2 = Sequence(
            [
                Resource("B", "agent"),
                level3,
            ]
        )
        level1 = Sequence(
            [
                Resource("A", "agent"),
                level2,
            ]
        )

        flattened = flatten_sequence(level1)
        assert len(flattened.nodes) == 4
        assert [n.name for n in flattened.nodes] == ["A", "B", "C", "D"]


class TestFlattenParallel:
    """Tests for flatten_parallel utility function."""

    def test_flatten_nested_parallel(self):
        """Test flattening nested parallel nodes."""
        inner = Parallel(
            [
                Resource("B", "agent"),
                Resource("C", "agent"),
            ]
        )
        outer = Parallel(
            [
                Resource("A", "agent"),
                inner,
                Resource("D", "agent"),
            ]
        )

        flattened = flatten_parallel(outer)
        assert isinstance(flattened, Parallel)
        assert len(flattened.nodes) == 4
        assert all(isinstance(node, Resource) for node in flattened.nodes)
        assert [n.name for n in flattened.nodes] == ["A", "B", "C", "D"]

    def test_flatten_non_parallel_unchanged(self):
        """Test that non-parallel nodes are unchanged."""
        resource = Resource("Test", "agent")
        result = flatten_parallel(resource)
        assert result is resource

        sequence = Sequence(
            [
                Resource("A", "agent"),
                Resource("B", "workflow"),
            ]
        )
        result = flatten_parallel(sequence)
        assert result is sequence

    def test_flatten_deeply_nested_parallel(self):
        """Test flattening deeply nested parallel nodes."""
        level3 = Parallel(
            [
                Resource("C", "agent"),
                Resource("D", "agent"),
            ]
        )
        level2 = Parallel(
            [
                Resource("B", "agent"),
                level3,
            ]
        )
        level1 = Parallel(
            [
                Resource("A", "agent"),
                level2,
            ]
        )

        flattened = flatten_parallel(level1)
        assert len(flattened.nodes) == 4
        assert [n.name for n in flattened.nodes] == ["A", "B", "C", "D"]


class TestComplexIRTrees:
    """Tests for complex IR tree structures."""

    def test_sequence_with_parallel_inside(self):
        """Test sequence containing parallel nodes."""
        tree = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Resource("Worker1", "agent"),
                        Resource("Worker2", "agent"),
                    ]
                ),
                Resource("End", "workflow"),
            ]
        )
        assert len(tree.nodes) == 3
        assert isinstance(tree.nodes[1], Parallel)

    def test_parallel_with_sequences_inside(self):
        """Test parallel containing sequence nodes."""
        tree = Parallel(
            [
                Sequence(
                    [
                        Resource("A1", "agent"),
                        Resource("A2", "workflow"),
                    ]
                ),
                Sequence(
                    [
                        Resource("B1", "agent"),
                        Resource("B2", "workflow"),
                    ]
                ),
            ]
        )
        assert len(tree.nodes) == 2
        assert all(isinstance(node, Sequence) for node in tree.nodes)

    def test_mixed_complex_tree(self):
        """Test complex tree with mixed operators."""
        tree = Sequence(
            [
                Resource("Init", "agent"),
                Parallel(
                    [
                        Resource("ParallelA", "agent"),
                        Sequence(
                            [
                                Resource("SeqB1", "workflow"),
                                Resource("SeqB2", "function"),
                            ]
                        ),
                    ]
                ),
                Resource("Finalize", "agent"),
            ]
        )
        assert isinstance(tree, Sequence)
        assert len(tree.nodes) == 3
        assert isinstance(tree.nodes[1], Parallel)
        assert isinstance(tree.nodes[1].nodes[1], Sequence)
