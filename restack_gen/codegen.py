"""Code generation from IR to Python pipeline code.

This module provides functions to generate Restack workflow pipeline code
from the Intermediate Representation (IR) tree created by the parser.
"""

from typing import Any

from restack_gen.ir import Conditional, IRNode, Parallel, Resource, Sequence


def generate_pipeline_code(ir: IRNode, pipeline_name: str, project_name: str) -> str:
    """
    Generate Python code for a Restack workflow pipeline from IR.

    Args:
        ir: The IR tree to generate code from
        pipeline_name: Name of the pipeline workflow (e.g., "DataPipeline")
        project_name: Name of the project for imports

    Returns:
        Generated Python code as a string

    Example:
        >>> ir = Sequence([Resource("A", "agent"), Resource("B", "agent")])
        >>> code = generate_pipeline_code(ir, "MyPipeline", "myproject")
    """
    # Generate imports
    imports = generate_imports(ir, project_name)
    imports_section = "\n".join(imports)

    # Generate the workflow execute method body
    body = _generate_node_code(ir, indent=2)

    # Build the complete workflow class
    code = f'''"""
{pipeline_name} workflow.

Auto-generated pipeline from operator expression.
"""

{imports_section}


class {pipeline_name}(Workflow):
    """Pipeline workflow: {pipeline_name}."""

    @step
    async def execute(self, input_data: dict) -> dict:
        """
        Execute the pipeline.

        Args:
            input_data: Input data for the pipeline

        Returns:
            Pipeline execution result
        """
{body}
        return result
'''

    return code


def generate_imports(ir: IRNode, project_name: str) -> list[str]:
    """
    Extract required imports from IR tree.

    Args:
        ir: The IR tree to analyze
        project_name: Name of the project for imports

    Returns:
        List of import statements needed
    """
    imports = [
        "from restack_ai import Workflow, step",
    ]

    # Collect all resources
    resources = _collect_resources(ir)

    # Group by type
    agents = [r.name for r in resources if r.resource_type == "agent"]
    workflows = [r.name for r in resources if r.resource_type == "workflow"]
    functions = [r.name for r in resources if r.resource_type == "function"]

    # Add imports for each type
    if agents:
        for agent in sorted(set(agents)):
            imports.append(
                f"from {project_name}.agents.{_to_snake_case(agent)} import {agent}"
            )

    if workflows:
        for workflow in sorted(set(workflows)):
            imports.append(
                f"from {project_name}.workflows.{_to_snake_case(workflow)} import {workflow}"
            )

    if functions:
        for func in sorted(set(functions)):
            imports.append(
                f"from {project_name}.functions.{_to_snake_case(func)} import {func}"
            )

    return imports


def _collect_resources(node: IRNode) -> list[Resource]:
    """Recursively collect all Resource nodes from IR tree."""
    if isinstance(node, Resource):
        return [node]

    resources = []
    if isinstance(node, Sequence):
        for child in node.nodes:
            resources.extend(_collect_resources(child))
    elif isinstance(node, Parallel):
        for child in node.nodes:
            resources.extend(_collect_resources(child))
    elif isinstance(node, Conditional):
        resources.extend(_collect_resources(node.condition))
        resources.extend(_collect_resources(node.true_branch))
        resources.extend(_collect_resources(node.false_branch))

    return resources


def _generate_node_code(node: IRNode, indent: int = 0, result_var: str = "result") -> str:
    """
    Generate code for an IR node.

    Args:
        node: The IR node to generate code for
        indent: Number of indentation levels (spaces = indent * 4)
        result_var: Variable name to store results in

    Returns:
        Generated Python code
    """
    if isinstance(node, Resource):
        return _generate_resource_code(node, indent, result_var)
    elif isinstance(node, Sequence):
        return generate_sequence_code(node, indent, result_var)
    elif isinstance(node, Parallel):
        return generate_parallel_code(node, indent, result_var)
    elif isinstance(node, Conditional):
        return generate_conditional_code(node, indent, result_var)
    else:
        raise ValueError(f"Unknown node type: {type(node)}")


def _generate_resource_code(resource: Resource, indent: int, result_var: str) -> str:
    """Generate code for a single Resource node."""
    spaces = " " * (indent * 4)
    activity_name = f"{_to_snake_case(resource.name)}_activity"

    return f"{spaces}{result_var} = await self.execute_activity({activity_name}, {result_var})\n"


def generate_sequence_code(sequence: Sequence, indent: int = 0, result_var: str = "result") -> str:
    """
    Generate code for a Sequence node (sequential execution).

    Args:
        sequence: The Sequence node
        indent: Indentation level
        result_var: Variable name for results

    Returns:
        Generated code for the sequence

    Example:
        A → B → C becomes:
            result = await self.execute_activity(a_activity, result)
            result = await self.execute_activity(b_activity, result)
            result = await self.execute_activity(c_activity, result)
    """
    code = ""
    for node in sequence.nodes:
        code += _generate_node_code(node, indent, result_var)
    return code


def generate_parallel_code(parallel: Parallel, indent: int = 0, result_var: str = "result") -> str:
    """
    Generate code for a Parallel node (concurrent execution).

    Args:
        parallel: The Parallel node
        indent: Indentation level
        result_var: Variable name for results

    Returns:
        Generated code using asyncio.gather

    Example:
        A ⇄ B ⇄ C becomes:
            results = await asyncio.gather(
                self.execute_activity(a_activity, result),
                self.execute_activity(b_activity, result),
                self.execute_activity(c_activity, result)
            )
            result = results  # or combine results
    """
    spaces = " " * (indent * 4)
    inner_spaces = " " * ((indent + 1) * 4)

    # For simple resources, generate gather call
    if all(isinstance(node, Resource) for node in parallel.nodes):
        activities = []
        for node in parallel.nodes:
            activity_name = f"{_to_snake_case(node.name)}_activity"
            activities.append(f"{inner_spaces}self.execute_activity({activity_name}, {result_var})")

        code = f"{spaces}results = await asyncio.gather(\n"
        code += ",\n".join(activities)
        code += f"\n{spaces})\n"
        code += f"{spaces}{result_var} = results\n"
        return code
    else:
        # Handle nested structures (more complex)
        code = f"{spaces}# TODO: Handle complex parallel execution\n"
        return code


def generate_conditional_code(conditional: Conditional, indent: int = 0, result_var: str = "result") -> str:
    """
    Generate code for a Conditional node (branching).

    Args:
        conditional: The Conditional node
        indent: Indentation level
        result_var: Variable name for results

    Returns:
        Generated if/else code

    Example:
        Conditional(condition="check_status", true_branch=B, false_branch=C) becomes:
            if result.get('check_status'):
                result = await self.execute_activity(b_activity, result)
            else:
                result = await self.execute_activity(c_activity, result)
    """
    spaces = " " * (indent * 4)
    inner_spaces = " " * ((indent + 1) * 4)

    code = ""

    # Add conditional branching using the string condition
    # The condition is a key in the result dictionary
    code += f"{spaces}if {result_var}.get('{conditional.condition}'):\n"
    code += _generate_node_code(conditional.true_branch, indent + 1, result_var)
    
    if conditional.false_branch:
        code += f"{spaces}else:\n"
        code += _generate_node_code(conditional.false_branch, indent + 1, result_var)

    return code


def _to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case.

    Args:
        name: PascalCase string (e.g., "DataCollector")

    Returns:
        snake_case string (e.g., "data_collector")
    """
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0 and name[i - 1].islower():
            result.append("_")
        result.append(char.lower())
    return "".join(result)
