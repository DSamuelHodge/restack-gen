"""Tests for code generation from IR to Python pipeline code."""

import ast

import pytest

from restack_gen.codegen import (
    _collect_resources,
    _to_snake_case,
    generate_conditional_code,
    generate_imports,
    generate_parallel_code,
    generate_pipeline_code,
    generate_sequence_code,
)
from restack_gen.ir import Conditional, Parallel, Resource, Sequence


class TestToSnakeCase:
    """Tests for PascalCase to snake_case conversion."""

    def test_simple_word(self):
        """Test single word conversion."""
        assert _to_snake_case("Agent") == "agent"

    def test_two_words(self):
        """Test two word conversion."""
        assert _to_snake_case("DataCollector") == "data_collector"

    def test_three_words(self):
        """Test three word conversion."""
        assert _to_snake_case("EmailDataProcessor") == "email_data_processor"

    def test_acronym(self):
        """Test acronym handling."""
        # Current implementation converts all caps to lowercase
        assert _to_snake_case("HTTPClient") == "httpclient"

    def test_already_lowercase(self):
        """Test already lowercase string."""
        assert _to_snake_case("agent") == "agent"


class TestCollectResources:
    """Tests for resource collection from IR tree."""

    def test_single_resource(self):
        """Test collecting from single Resource node."""
        resource = Resource("Agent1", "agent")
        resources = _collect_resources(resource)
        assert len(resources) == 1
        assert resources[0].name == "Agent1"

    def test_sequence_resources(self):
        """Test collecting from Sequence."""
        seq = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Workflow1", "workflow"),
                Resource("Function1", "function"),
            ]
        )
        resources = _collect_resources(seq)
        assert len(resources) == 3
        assert [r.name for r in resources] == ["Agent1", "Workflow1", "Function1"]

    def test_parallel_resources(self):
        """Test collecting from Parallel."""
        par = Parallel(
            [Resource("Agent1", "agent"), Resource("Agent2", "agent")]
        )
        resources = _collect_resources(par)
        assert len(resources) == 2

    def test_nested_structure(self):
        """Test collecting from nested structure."""
        seq = Sequence(
            [
                Resource("Agent1", "agent"),
                Parallel(
                    [
                        Resource("Agent2", "agent"),
                        Resource("Agent3", "agent"),
                    ]
                ),
                Resource("Agent4", "agent"),
            ]
        )
        resources = _collect_resources(seq)
        assert len(resources) == 4
        assert [r.name for r in resources] == ["Agent1", "Agent2", "Agent3", "Agent4"]


class TestGenerateImports:
    """Tests for import generation."""

    def test_single_agent_import(self):
        """Test import for a single agent."""
        ir = Resource("DataCollector", "agent")
        imports = generate_imports(ir, "myproject")

        assert "from restack_ai import Workflow, step" in imports
        assert "from myproject.agents.data_collector import DataCollector" in imports

    def test_multiple_resource_types(self):
        """Test imports for mixed resource types."""
        ir = Sequence(
            [
                Resource("DataCollector", "agent"),
                Resource("ProcessWorkflow", "workflow"),
                Resource("transform_data", "function"),
            ]
        )
        imports = generate_imports(ir, "myproject")

        assert "from myproject.agents.data_collector import DataCollector" in imports
        assert "from myproject.workflows.process_workflow import ProcessWorkflow" in imports
        assert "from myproject.functions.transform_data import transform_data" in imports

    def test_duplicate_resources(self):
        """Test that duplicate resources only generate one import."""
        ir = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent1", "agent"),
                Resource("Agent1", "agent"),
            ]
        )
        imports = generate_imports(ir, "myproject")

        # Should only have one import for Agent1
        agent_imports = [imp for imp in imports if "Agent1" in imp]
        assert len(agent_imports) == 1


class TestGenerateSequenceCode:
    """Tests for sequence code generation."""

    def test_two_resources(self):
        """Test sequence of two resources."""
        seq = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        code = generate_sequence_code(seq, indent=2)

        assert "result = await self.execute_activity(agent1_activity, result)" in code
        assert "result = await self.execute_activity(agent2_activity, result)" in code

    def test_three_resources(self):
        """Test sequence of three resources."""
        seq = Sequence(
            [
                Resource("Fetcher", "agent"),
                Resource("Processor", "agent"),
                Resource("Saver", "agent"),
            ]
        )
        code = generate_sequence_code(seq, indent=2)

        assert "fetcher_activity" in code
        assert "processor_activity" in code
        assert "saver_activity" in code
        assert code.count("await self.execute_activity") == 3

    def test_indentation(self):
        """Test proper indentation."""
        seq = Sequence([Resource("Agent1", "agent"), Resource("Agent2", "agent")])
        code = generate_sequence_code(seq, indent=2)

        # Should start with 8 spaces (2 * 4)
        lines = code.split("\n")
        # First non-empty line should have 8 spaces
        assert lines[0].startswith("        ")


class TestGenerateParallelCode:
    """Tests for parallel code generation."""

    def test_two_resources(self):
        """Test parallel execution of two resources."""
        par = Parallel(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        code = generate_parallel_code(par, indent=2)

        assert "asyncio.gather" in code
        assert "agent1_activity" in code
        assert "agent2_activity" in code

    def test_three_resources(self):
        """Test parallel execution of three resources."""
        par = Parallel(
            [
                Resource("Worker1", "agent"),
                Resource("Worker2", "agent"),
                Resource("Worker3", "agent"),
            ]
        )
        code = generate_parallel_code(par, indent=2)

        assert "asyncio.gather" in code
        assert code.count("execute_activity") == 3


class TestGenerateConditionalCode:
    """Tests for conditional code generation."""

    def test_simple_conditional(self):
        """Test simple if/else branching."""
        cond = Conditional(
            condition="check_status",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        code = generate_conditional_code(cond, indent=2)

        assert "if result.get('check_status'):" in code
        assert "handler1_activity" in code
        assert "else:" in code
        assert "handler2_activity" in code


class TestGeneratePipelineCode:
    """Tests for complete pipeline code generation."""

    def test_simple_sequence_pipeline(self):
        """Test generating code for a simple sequence."""
        ir = Sequence(
            [
                Resource("Fetcher", "agent"),
                Resource("Processor", "agent"),
                Resource("Saver", "agent"),
            ]
        )
        code = generate_pipeline_code(ir, "DataPipeline", "myproject")

        # Check structure
        assert "class DataPipeline(Workflow):" in code
        assert "async def execute(self, input_data: dict) -> dict:" in code
        assert "@step" in code

        # Check imports
        assert "from restack_ai import Workflow, step" in code
        assert "from myproject.agents.fetcher import Fetcher" in code
        assert "from myproject.agents.processor import Processor" in code
        assert "from myproject.agents.saver import Saver" in code

        # Check execution
        assert "fetcher_activity" in code
        assert "processor_activity" in code
        assert "saver_activity" in code
        assert "return result" in code

    def test_parallel_pipeline(self):
        """Test generating code for parallel execution."""
        ir = Parallel(
            [
                Resource("Worker1", "agent"),
                Resource("Worker2", "agent"),
            ]
        )
        code = generate_pipeline_code(ir, "ParallelPipeline", "myproject")

        assert "asyncio.gather" in code
        assert "worker1_activity" in code
        assert "worker2_activity" in code

    def test_sequence_with_parallel(self):
        """Test sequence containing parallel execution."""
        ir = Sequence(
            [
                Resource("Input", "agent"),
                Parallel(
                    [
                        Resource("ProcessA", "agent"),
                        Resource("ProcessB", "agent"),
                    ]
                ),
                Resource("Output", "agent"),
            ]
        )
        code = generate_pipeline_code(ir, "MixedPipeline", "myproject")

        assert "input_activity" in code
        assert "asyncio.gather" in code
        assert "process_a_activity" in code
        assert "process_b_activity" in code
        assert "output_activity" in code

    def test_conditional_pipeline(self):
        """Test conditional branching pipeline."""
        ir = Conditional(
            condition="needs_processing",
            true_branch=Resource("Handler1", "agent"),
            false_branch=Resource("Handler2", "agent"),
        )
        code = generate_pipeline_code(ir, "ConditionalPipeline", "myproject")

        assert "if result.get('needs_processing'):" in code
        assert "handler1_activity" in code
        assert "else:" in code
        assert "handler2_activity" in code


class TestCodeValidation:
    """Tests for generated code validation."""

    def test_generated_code_syntax(self):
        """Test that generated code is syntactically valid Python."""
        ir = Sequence(
            [
                Resource("Agent1", "agent"),
                Resource("Agent2", "agent"),
            ]
        )
        code = generate_pipeline_code(ir, "TestPipeline", "testproject")

        # This should not raise SyntaxError
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_parallel_code_syntax(self):
        """Test that parallel code is syntactically valid."""
        ir = Parallel(
            [
                Resource("Worker1", "agent"),
                Resource("Worker2", "agent"),
                Resource("Worker3", "agent"),
            ]
        )
        code = generate_pipeline_code(ir, "ParallelPipeline", "testproject")

        # This should not raise SyntaxError
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated parallel code has syntax error: {e}")

    def test_conditional_code_syntax(self):
        """Test that conditional code is syntactically valid."""
        ir = Conditional(
            condition="should_process",
            true_branch=Sequence(
                [Resource("A", "agent"), Resource("B", "agent")]
            ),
            false_branch=Resource("C", "agent"),
        )
        code = generate_pipeline_code(ir, "ConditionalPipeline", "testproject")

        # This should not raise SyntaxError
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated conditional code has syntax error: {e}")

    def test_complex_nested_syntax(self):
        """Test complex nested structure is valid."""
        ir = Sequence(
            [
                Resource("Start", "agent"),
                Parallel(
                    [
                        Sequence(
                            [
                                Resource("A1", "agent"),
                                Resource("A2", "agent"),
                            ]
                        ),
                        Sequence(
                            [
                                Resource("B1", "agent"),
                                Resource("B2", "agent"),
                            ]
                        ),
                    ]
                ),
                Resource("End", "agent"),
            ]
        )
        code = generate_pipeline_code(ir, "ComplexPipeline", "testproject")

        # This should not raise SyntaxError
        try:
            ast.parse(code)
        except SyntaxError as e:
            pytest.fail(f"Generated complex code has syntax error: {e}")
