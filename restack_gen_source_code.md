# Restack Generator - Source Code Documentation

This document contains all Python source files from the `restack_gen` package.

**Total files:** 13

---

## Table of Contents

1. [restack_gen\__init__.py](#restack_gen-__init__-py)
2. [restack_gen\ast_service.py](#restack_gen-ast_service-py)
3. [restack_gen\cli.py](#restack_gen-cli-py)
4. [restack_gen\codegen.py](#restack_gen-codegen-py)
5. [restack_gen\compat.py](#restack_gen-compat-py)
6. [restack_gen\doctor.py](#restack_gen-doctor-py)
7. [restack_gen\generator.py](#restack_gen-generator-py)
8. [restack_gen\ir.py](#restack_gen-ir-py)
9. [restack_gen\parser.py](#restack_gen-parser-py)
10. [restack_gen\project.py](#restack_gen-project-py)
11. [restack_gen\renderer.py](#restack_gen-renderer-py)
12. [restack_gen\runner.py](#restack_gen-runner-py)
13. [restack_gen\validator.py](#restack_gen-validator-py)

---

## restack_gen\__init__.py

<a id="restack_gen-__init__-py"></a>

**File:** `restack_gen\__init__.py`

```python
"""Restack Gen - Rails-style scaffolding CLI for Restack agents, workflows, and pipelines."""

__version__ = "1.0.0"
__author__ = "Rails Team"
__email__ = "team@thethinking.company"

from restack_gen.cli import app

__all__ = ["app", "__version__"]
```

---

## restack_gen\ast_service.py

<a id="restack_gen-ast_service-py"></a>

**File:** `restack_gen\ast_service.py`

```python
"""AST utilities for modifying service.py."""

import ast
import re
from pathlib import Path


class ServiceModificationError(Exception):
    """Raised when service.py modification fails."""


def parse_service_file(service_path: Path) -> ast.Module:
    """Parse service.py into an AST.

    Args:
        service_path: Path to service.py file

    Returns:
        Parsed AST module

    Raises:
        ServiceModificationError: If file cannot be parsed
    """
    try:
        with open(service_path, encoding="utf-8") as f:
            source = f.read()
        return ast.parse(source)
    except Exception as e:
        raise ServiceModificationError(f"Failed to parse service.py: {e}") from e


def find_import_section_end(tree: ast.Module) -> int:
    """Find the line number where imports end.

    Looks for the last import statement and returns its line number.

    Args:
        tree: AST module

    Returns:
        Line number after last import (0-indexed in AST terms)
    """
    last_import_line = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if hasattr(node, "lineno"):
                last_import_line = max(last_import_line, node.lineno)
    return last_import_line


def has_import(tree: ast.Module, module: str, names: list[str]) -> bool:
    """Check if specific import already exists.

    Args:
        tree: AST module
        module: Module name (e.g., 'myapp.agents.researcher')
        names: Names to import (e.g., ['ResearcherAgent'])

    Returns:
        True if import exists
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == module:
                imported_names = {alias.name for alias in node.names}
                if all(name in imported_names for name in names):
                    return True
    return False


def add_import(source: str, module: str, names: list[str], comment: str | None = None) -> str:
    """Add an import statement to service.py source.

    Finds the appropriate location (after existing imports from same package)
    and inserts the new import.

    Args:
        source: Current source code
        module: Module to import from (e.g., 'myapp.agents.researcher')
        names: Names to import (e.g., ['ResearcherAgent'])
        comment: Optional comment line to add before import block

    Returns:
        Modified source code
    """
    tree = ast.parse(source)

    # Check if import already exists
    if has_import(tree, module, names):
        return source

    lines = source.split("\n")

    # Find the package prefix (e.g., 'myapp')
    package_prefix = module.split(".")[0]
    resource_type = module.split(".")[1] if len(module.split(".")) > 1 else None

    # Find where to insert based on resource type
    insert_line = None
    last_matching_import = None

    for i, line in enumerate(lines):
        # Look for import section comments
        if resource_type == "agents" and "# Agents" in line:
            insert_line = i + 1
            # Skip to end of agents section
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("from") or not lines[j].strip()):
                if lines[j].strip().startswith("from"):
                    last_matching_import = j
                j += 1
            if last_matching_import:
                insert_line = last_matching_import + 1
            break
        elif resource_type == "workflows" and "# Workflows" in line:
            insert_line = i + 1
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("from") or not lines[j].strip()):
                if lines[j].strip().startswith("from"):
                    last_matching_import = j
                j += 1
            if last_matching_import:
                insert_line = last_matching_import + 1
            break
        elif resource_type == "functions" and "# Functions" in line:
            insert_line = i + 1
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("from") or not lines[j].strip()):
                if lines[j].strip().startswith("from"):
                    last_matching_import = j
                j += 1
            if last_matching_import:
                insert_line = last_matching_import + 1
            break

    # If no matching section found, insert after settings import
    if insert_line is None:
        for i, line in enumerate(lines):
            if f"from {package_prefix}.common.settings import settings" in line:
                insert_line = i + 1
                # Add the section comment
                if resource_type == "agents":
                    lines.insert(insert_line, "\n# Agents")
                    insert_line += 2
                elif resource_type == "workflows":
                    lines.insert(insert_line, "\n# Workflows")
                    insert_line += 2
                elif resource_type == "functions":
                    lines.insert(insert_line, "\n# Functions")
                    insert_line += 2
                break

    # Insert the import
    if insert_line is not None:
        import_line = f"from {module} import {', '.join(names)}"
        lines.insert(insert_line, import_line)

    return "\n".join(lines)


def find_list_argument(call_node: ast.Call, arg_name: str) -> ast.List | None:
    """Find a list argument in a function call.

    Args:
        call_node: AST Call node
        arg_name: Name of the keyword argument

    Returns:
        AST List node if found
    """
    for keyword in call_node.keywords:
        if keyword.arg == arg_name and isinstance(keyword.value, ast.List):
            return keyword.value
    return None


def add_to_list_in_source(source: str, list_name: str, item: str) -> str:
    """Add an item to a list argument in start_service call.

    Args:
        source: Current source code
        list_name: Name of list argument ('workflows' or 'functions')
        item: Item to add (e.g., 'ResearcherAgent')

    Returns:
        Modified source code
    """
    tree = ast.parse(source)

    # Find the start_service call
    start_service_call = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "start_service":
                    start_service_call = node
                    break

    if not start_service_call:
        raise ServiceModificationError("Could not find start_service call")

    # Find the list argument
    list_arg = find_list_argument(start_service_call, list_name)
    if list_arg is None:
        raise ServiceModificationError(f"Could not find {list_name}= argument")

    # Check if item already exists
    for elem in list_arg.elts:
        if isinstance(elem, ast.Name) and elem.id == item:
            return source  # Already exists

    # Find the list in source and add item
    lines = source.split("\n")

    # Find the list by looking for "list_name=["
    list_start_line = None
    in_start_service = False
    for i, line in enumerate(lines):
        if "start_service(" in line:
            in_start_service = True
        if in_start_service and f"{list_name}=" in line:
            list_start_line = i
            break

    if list_start_line is None:
        raise ServiceModificationError(f"Could not find {list_name}= in source")

    # Find the closing bracket of this list
    bracket_count = 0
    found_opening = False
    list_end_line = None

    for i in range(list_start_line, len(lines)):
        line = lines[i]
        for char in line:
            if char == "[":
                bracket_count += 1
                found_opening = True
            elif char == "]":
                bracket_count -= 1
                if found_opening and bracket_count == 0:
                    list_end_line = i
                    break
        if list_end_line is not None:
            break

    if list_end_line is None:
        raise ServiceModificationError(f"Could not find closing bracket for {list_name}")

    # Check if it's a single-line list (opening and closing on same line)
    if list_start_line == list_end_line:
        # Single-line list like "workflows=[        ]," - need to expand to multi-line
        line = lines[list_start_line]
        indent_match = re.match(r"^(\s*)", line)
        base_indent = indent_match.group(1) if indent_match else ""
        item_indent = base_indent + "    "

        # Replace the single line with multi-line format
        list_name_part = line[: line.index("[")]
        lines[list_start_line] = f"{list_name_part}["
        lines.insert(list_start_line + 1, f"{item_indent}{item},")
        lines.insert(list_start_line + 2, f"{base_indent}],")
    else:
        # Multi-line list - determine indentation from existing items or default
        item_indent = None
        for i in range(list_start_line + 1, list_end_line):
            line = lines[i]
            if line.strip() and not line.strip().startswith("#"):
                # Found an existing item, use its indentation
                indent_match = re.match(r"^(\s*)", line)
                if indent_match:
                    item_indent = indent_match.group(1)
                break

        # If no existing items, determine indent from the opening bracket line
        if item_indent is None:
            indent_match = re.match(r"^(\s*)", lines[list_start_line])
            base_indent = indent_match.group(1) if indent_match else ""
            item_indent = base_indent + "    "

        # Insert before closing bracket
        lines.insert(list_end_line, f"{item_indent}{item},")

    return "\n".join(lines)


def write_service_file(source: str, service_path: Path) -> None:
    """Write modified source back to service.py.

    Args:
        source: Modified source code
        service_path: Path to service.py file

    Raises:
        ServiceModificationError: If file cannot be written
    """
    try:
        with open(service_path, "w", encoding="utf-8") as f:
            f.write(source)
    except Exception as e:
        raise ServiceModificationError(f"Failed to write service.py: {e}") from e


def update_service_file(
    service_path: Path,
    resource_type: str,
    module_name: str,
    import_name: str,
    module_prefix: str | None = None,
) -> None:
    """Update service.py with new resource.

    Adds import and registers resource in appropriate list.

    Args:
        service_path: Path to service.py file
        resource_type: Type of resource ('agent', 'workflow', or 'function')
        module_name: Module name (e.g., 'researcher' for agents/researcher.py)
        import_name: Name to import and register (e.g., 'ResearcherAgent' or 'research')
        module_prefix: Optional module prefix override for import path

    Raises:
        ServiceModificationError: If modification fails
        ValueError: If resource_type is invalid
    """
    if resource_type not in ["agent", "workflow", "function"]:
        raise ValueError(f"Invalid resource_type: {resource_type}")

    # Read current source
    with open(service_path, encoding="utf-8") as f:
        source = f.read()

    # Extract project name from first import
    tree = ast.parse(source)
    project_name = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if ".common.settings" in node.module:
                project_name = node.module.split(".")[0]
                break

    if not project_name:
        raise ServiceModificationError("Could not determine project name from imports")

    # Build import module path
    if resource_type == "agent":
        default_prefix = f"{project_name}.agents"
        list_name = "workflows"  # Agents are registered as workflows
    elif resource_type == "workflow":
        default_prefix = f"{project_name}.workflows"
        list_name = "workflows"
    else:  # function
        default_prefix = f"{project_name}.functions"
        list_name = "functions"

    import_prefix = module_prefix if module_prefix is not None else default_prefix
    import_module = f"{import_prefix}.{module_name}"

    # Add import
    source = add_import(source, import_module, [import_name])

    # Add to list
    source = add_to_list_in_source(source, list_name, import_name)

    # Write back
    write_service_file(source, service_path)
```

---

## restack_gen\cli.py

<a id="restack_gen-cli-py"></a>

**File:** `restack_gen\cli.py`

```python
"""Main CLI application using Typer.

This module implements the Rails-style scaffolding commands for Restack.
"""

from typing import Annotated

import typer
from rich.console import Console

from restack_gen import __version__
from restack_gen import doctor as doctor_mod
from restack_gen import runner as runner_mod
from restack_gen.generator import (
    GenerationError,
    generate_agent,
    generate_function,
    generate_llm_config,
    generate_pipeline,
    generate_prompt,
    generate_tool_server,
    generate_workflow,
)
from restack_gen.project import create_new_project

app = typer.Typer(
    name="restack",
    help="Rails-style scaffolding CLI for Restack agents, workflows, and pipelines",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold green]restack-gen[/bold green] version [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """
    🚀 Restack Gen - Rails for Restack Agents

    Convention-over-configuration scaffolding for building Restack agents,
    workflows, and pipelines with fault-tolerance baked in.
    """
    pass


@app.command()
def new(
    app_name: Annotated[str, typer.Argument(help="Name of the application to create")],
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing directory")] = False,
) -> None:
    """
    Create a new Restack application with omakase layout and configuration.

    Example:
        restack new myapp
    """
    try:
        console.print(f"[yellow]Creating new app:[/yellow] [bold]{app_name}[/bold]")

        project_path = create_new_project(app_name, force=force)

        console.print(f"[green]✓[/green] Created project at: [bold]{project_path}[/bold]")
        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print(f"  cd {app_name}")
        console.print("  make setup      # Install dependencies")
        console.print("  make test       # Run tests")
        console.print("\n[bold cyan]Generate resources:[/bold cyan]")
        console.print("  restack g agent MyAgent")
        console.print("  restack g workflow MyWorkflow")
        console.print("  restack g function my_function")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except FileExistsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="g")
def generate(
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Type of resource: agent, workflow, function, pipeline, tool-server, llm-config, or prompt"
        ),
    ],
    name: Annotated[str | None, typer.Argument(help="Name of the resource to generate")] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing files")] = False,
    operators: Annotated[
        str | None,
        typer.Option(
            "--operators", "-o", help="Operator expression for pipeline (e.g., 'A → B ⇄ C')"
        ),
    ] = None,
    backend: Annotated[
        str, typer.Option("--backend", help="Backend type for llm-config (direct or kong)")
    ] = "direct",
    version: Annotated[str, typer.Option("--version", help="Prompt version (semver)")] = "1.0.0",
    with_llm: Annotated[
        bool,
        typer.Option(
            "--with-llm", help="Generate agent with LLM router and prompt loader capabilities"
        ),
    ] = False,
    tools: Annotated[
        str | None,
        typer.Option("--tools", help="FastMCP tool server to integrate (e.g., 'Research')"),
    ] = None,
) -> None:
    """
    Generate a new resource (agent, workflow, function, pipeline, tool-server, llm-config, or prompt).

    Examples:
        restack g agent Researcher
        restack g agent Researcher --with-llm
        restack g agent Researcher --tools Research
        restack g agent Researcher --with-llm --tools Research
        restack g workflow EmailCampaign
        restack g function send_email
        restack g pipeline DataPipeline --operators "Fetch → Process ⇄ Store"
        restack g tool-server Research
    restack g llm-config
        restack g llm-config --backend kong
    restack g prompt AnalyzeResearch --version 1.0.0
    """
    try:
        if resource_type == "llm-config":
            files = generate_llm_config(force=force, backend=backend)
            console.print("[green]✓[/green] Generated LLM router configuration")
            console.print(f"  Config: {files['config']}")
            console.print(f"  Router: {files['router']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Set environment variables:")
            console.print("     export OPENAI_API_KEY=sk-...")
            if backend == "kong":
                console.print("     export KONG_GATEWAY_URL=http://localhost:8000")
            console.print("  2. Configure providers in config/llm_router.yaml")
            console.print("  3. Use LLMRouter in your agents")
            return

        if not name:
            console.print(f"[red]Error:[/red] Name is required for {resource_type}")
            raise typer.Exit(1)

        if resource_type == "agent":
            files = generate_agent(name, force=force, with_llm=with_llm, tools_server=tools)
            console.print(f"[green]✓[/green] Generated agent: [bold]{name}[/bold]")
            if with_llm:
                console.print("  [cyan]Enhanced with:[/cyan] LLM router & prompt loader")
            if tools:
                console.print(f"  [cyan]Enhanced with:[/cyan] FastMCP tools ({tools})")
            console.print(f"  Agent: {files['agent']}")
            console.print(f"  Test: {files['test']}")
            console.print(f"  Client: {files['client']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Implement agent logic in the generated file")
            if with_llm:
                console.print("  2. Configure LLM providers: restack g llm-config")
                console.print("  3. Create prompts: restack g prompt YourPrompt")
            if tools:
                console.print(f"  2. Ensure tool server exists: restack g tool-server {tools}")
            console.print("  2. Run tests: make test")
            console.print(f"  3. Schedule agent: python {files['client']}")

        elif resource_type == "workflow":
            files = generate_workflow(name, force=force)
            console.print(f"[green]✓[/green] Generated workflow: [bold]{name}[/bold]")
            console.print(f"  Workflow: {files['workflow']}")
            console.print(f"  Test: {files['test']}")
            console.print(f"  Client: {files['client']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Implement workflow logic in the generated file")
            console.print("  2. Run tests: make test")
            console.print(f"  3. Execute workflow: python {files['client']}")

        elif resource_type == "function":
            files = generate_function(name, force=force)
            console.print(f"[green]✓[/green] Generated function: [bold]{name}[/bold]")
            console.print(f"  Function: {files['function']}")
            console.print(f"  Test: {files['test']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Implement function logic in the generated file")
            console.print("  2. Run tests: make test")
            console.print("  3. Use in workflows or call directly")

        elif resource_type == "pipeline":
            if not operators:
                console.print("[red]Error:[/red] Pipeline generation requires --operators option")
                console.print(
                    'Example: restack g pipeline DataPipeline --operators "Fetch → Process"'
                )
                raise typer.Exit(1)

            files = generate_pipeline(name, operators, force=force)
            console.print(f"[green]✓[/green] Generated pipeline: [bold]{name}[/bold]")
            console.print(f"  Workflow: {files['workflow']}")
            console.print(f"  Test: {files['test']}")
            console.print("\n[bold cyan]Pipeline structure:[/bold cyan]")
            console.print(f"  Operators: {operators}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Review generated workflow code")
            console.print("  2. Ensure all referenced resources exist")
            console.print("  3. Run tests: make test")

        elif resource_type == "tool-server":
            files = generate_tool_server(name, force=force)
            console.print(f"[green]✓[/green] Generated FastMCP tool server: [bold]{name}[/bold]")
            console.print(f"  Server: {files['server']}")
            if files.get("config"):
                console.print(f"  Config: {files['config']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Implement your custom tools in the generated file")
            console.print("  2. Set environment variables (e.g., BRAVE_API_KEY)")
            console.print("  3. Test server: python -m pytest")
            console.print("  4. Run server: python " + str(files["server"]))

        elif resource_type == "prompt":
            files = generate_prompt(name, version=version, force=force)
            console.print(f"[green]✓[/green] Generated prompt: [bold]{name}[/bold] v{version}")
            console.print(f"  Prompt file: {files['prompt']}")
            console.print(f"  Registry: {files['config']}")
            if files.get("loader"):
                console.print(f"  Loader: {files['loader']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Edit the markdown template to fit your use case")
            console.print("  2. Load prompts via PromptLoader in your agents")
            console.print(
                "  3. Add more versions with --version and update 'latest' if appropriate"
            )

        else:
            console.print(f"[red]Error:[/red] Unknown resource type: {resource_type}")
            console.print(
                "Valid types: agent, workflow, function, pipeline, tool-server, llm-config, prompt"
            )
            raise typer.Exit(1)

    except GenerationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command(name="run:server")
def run_server(
    config: Annotated[
        str, typer.Option("--config", "-c", help="Path to config file")
    ] = "config/settings.yaml",
) -> None:
    """
    Start the Restack service (registers agents, workflows, functions).

    Example:
        restack run:server
        restack run:server --config config/prod.yaml
    """
    try:
        console.print("[cyan]Starting Restack service...[/cyan]")
        with console.status(
            "Starting service (registering workflows/functions)...", spinner="dots"
        ):
            runner_mod.start_service(config_path=config)
    except runner_mod.RunnerError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        raise typer.Exit(code=1) from None


@app.command()
def doctor(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
    check_tools: Annotated[
        bool, typer.Option("--check-tools", help="Check FastMCP tool servers")
    ] = False,
) -> None:
    """
    Check environment, configuration, dependencies, and connectivity.

    Validates:
    - Python version (3.11+)
    - Package versions
    - Engine connectivity
    - Import resolution
    - File permissions
    - Git status
    - FastMCP tool servers (with --check-tools)

    Example:
        restack doctor
        restack doctor --verbose
        restack doctor --check-tools
    """
    console.print("[yellow]Running doctor checks...[/yellow]")
    with console.status("Evaluating environment, config, and connectivity...", spinner="earth"):
        results = doctor_mod.run_all_checks(
            base_dir=".", verbose=verbose, check_tools_flag=check_tools
        )

    def _badge(status: str) -> str:
        return {
            "ok": "[green]✓[/green]",
            "warn": "[yellow]![/yellow]",
            "fail": "[red]✗[/red]",
        }.get(status, "-")

    for r in results:
        line = f"{_badge(r.status)} [bold]{r.name}[/bold]: {r.message}"
        console.print(line)
        if verbose and r.details:
            console.print(f"    [dim]{r.details}[/dim]")

    summary = doctor_mod.summarize(results)
    console.print()
    console.print(
        f"Overall: [bold]{summary['overall']}[/bold] • ok={summary['ok']} warn={summary['warn']} fail={summary['fail']}"
    )

    if summary["overall"] == "fail":
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
```

---

## restack_gen\codegen.py

<a id="restack_gen-codegen-py"></a>

**File:** `restack_gen\codegen.py`

```python
"""Code generation from IR to Python pipeline code.

This module provides functions to generate Restack workflow pipeline code
from the Intermediate Representation (IR) tree created by the parser.
"""

from typing import cast

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
    imports: list[str] = []

    if _requires_asyncio(ir):
        imports.append("import asyncio")

    imports.append("from restack_ai import Workflow, step")

    # Collect all resources
    resources = _collect_resources(ir)

    # Group by type
    agents = [r.name for r in resources if r.resource_type == "agent"]
    workflows = [r.name for r in resources if r.resource_type == "workflow"]
    functions = [r.name for r in resources if r.resource_type == "function"]

    # Add imports for each type
    if agents:
        for agent in sorted(set(agents)):
            module_name = _to_snake_case(agent)
            activity_name = f"{module_name}_activity"
            imports.append(f"from agents.{module_name} import {activity_name}")

    if workflows:
        for workflow in sorted(set(workflows)):
            base_name = _to_snake_case(workflow)
            module_name = f"{base_name}_workflow"
            activity_name = f"{base_name}_activity"
            imports.append(f"from workflows.{module_name} import {activity_name}")

    if functions:
        for func in sorted(set(functions)):
            module_name = _to_snake_case(func)
            activity_name = f"{module_name}_activity"
            imports.append(f"from functions.{module_name} import {activity_name}")

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
        resources.extend(_collect_resources(node.true_branch))
        if node.false_branch is not None:
            resources.extend(_collect_resources(node.false_branch))

    return resources


def _requires_asyncio(node: IRNode) -> bool:
    """Check if generated code needs asyncio imports."""
    if isinstance(node, Parallel):
        return True

    if isinstance(node, Sequence):
        return any(_requires_asyncio(child) for child in node.nodes)

    if isinstance(node, Conditional):
        if _requires_asyncio(node.true_branch):
            return True
        if node.false_branch is not None and _requires_asyncio(node.false_branch):
            return True

    return False


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
        activities: list[str] = []
        resources: list[Resource] = [cast(Resource, n) for n in parallel.nodes]
        for res in resources:
            activity_name = f"{_to_snake_case(res.name)}_activity"
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


def generate_conditional_code(
    conditional: Conditional, indent: int = 0, result_var: str = "result"
) -> str:
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
```

---

## restack_gen\compat.py

<a id="restack_gen-compat-py"></a>

**File:** `restack_gen\compat.py`

```python
"""Pydantic v1/v2 compatibility shim.

This module provides a unified interface for Pydantic v1 and v2,
allowing generated projects to work with either version.
"""

from __future__ import annotations

from typing import Any

# Base classes selected at runtime
BaseModelBase: Any
SettingsBaseBase: Any

try:
    # Prefer Pydantic v2
    from pydantic import BaseModel as _BaseModelV2
    from pydantic import Field as _Field
    from pydantic import ValidationError
    from pydantic_settings import BaseSettings as _BaseSettingsV2

    PYDANTIC_V2 = True
    BaseModelBase = _BaseModelV2
    SettingsBaseBase = _BaseSettingsV2
    Field = _Field
except ImportError:
    # Fall back to Pydantic v1
    from pydantic import BaseModel as _BaseModelV1
    from pydantic import BaseSettings as _BaseSettingsV1
    from pydantic import Field as _FieldV1
    from pydantic import ValidationError

    PYDANTIC_V2 = False
    BaseModelBase = _BaseModelV1
    SettingsBaseBase = _BaseSettingsV1
    Field = _FieldV1


class BaseModel(BaseModelBase):  # type: ignore[misc]
    """Compatibility BaseModel wrapper for Pydantic v1/v2."""

    if PYDANTIC_V2:
        model_config = {"arbitrary_types_allowed": True, "validate_assignment": True}
    else:

        class Config:
            arbitrary_types_allowed = True
            validate_assignment = True

    @classmethod
    def from_yaml(cls: type[BaseModel], path: str) -> BaseModel:
        """Load model from YAML file."""
        from pathlib import Path

        import yaml

        yaml_path = Path(path)
        if not yaml_path.exists():
            # Return default instance if file doesn't exist
            return cls()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)
            return cls(**data) if data else cls()


class SettingsBase(SettingsBaseBase):  # type: ignore[misc]
    """Compatibility Settings wrapper for Pydantic v1/v2."""

    if PYDANTIC_V2:
        model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
    else:

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

    @classmethod
    def from_yaml(cls: type[SettingsBase], path: str) -> SettingsBase:
        """Load settings from YAML file."""
        from pathlib import Path

        import yaml

        yaml_path = Path(path)
        if not yaml_path.exists():
            return cls()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)
            return cls(**data) if data else cls()


__all__ = ["BaseModel", "Field", "SettingsBase", "ValidationError", "PYDANTIC_V2"]
```

---

## restack_gen\doctor.py

<a id="restack_gen-doctor-py"></a>

**File:** `restack_gen\doctor.py`

```python
"""Environment and project health checks for `restack-gen`.

This module implements a set of checks used by the `restack doctor` command
to verify the local environment, dependencies, and basic project structure.

Design goals:
- Keep checks fast and side-effect free
- Return structured results that the CLI can render
- Be resilient: unexpected environments should degrade to warnings, not crash
"""

from __future__ import annotations

import asyncio
import importlib
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import httpx
import yaml

Status = Literal["ok", "warn", "fail"]


@dataclass
class DoctorCheckResult:
    """Result of a single doctor check."""

    name: str
    status: Status
    message: str
    details: str | None = None


def _status_priority(status: Status) -> int:
    return {"ok": 0, "warn": 1, "fail": 2}[status]


def check_python_version(min_major: int = 3, min_minor: int = 11) -> DoctorCheckResult:
    """Ensure Python >= min_major.min_minor.

    Defaults to 3.11+ as our recommended baseline.
    """
    py = sys.version_info
    meets = (py.major, py.minor) >= (min_major, min_minor)
    status: Status = "ok" if meets else "fail"
    msg = f"Python {py.major}.{py.minor}.{py.micro} detected; required >= {min_major}.{min_minor}"
    return DoctorCheckResult("python_version", status, msg)


def check_dependencies(packages: Iterable[str] = ("typer", "rich", "jinja2")) -> DoctorCheckResult:
    """Verify core Python package dependencies are importable.

    We only check for importability, not exact versions, to keep this
    environment-agnostic. The CLI can surface details.
    """
    missing: list[str] = []
    for pkg in packages:
        try:
            importlib.import_module(pkg)
        except Exception:  # pragma: no cover - any import error treated the same
            missing.append(pkg)

    if missing:
        return DoctorCheckResult(
            name="dependencies",
            status="warn",
            message="Some optional dependencies are not importable",
            details=", ".join(sorted(missing)),
        )

    return DoctorCheckResult("dependencies", "ok", "Core dependencies are importable")


def check_package_versions() -> DoctorCheckResult:
    """Check installed package versions against recommended minimums.

    Validates:
    - restack-ai >= 1.2.3
    - pydantic >= 2.7.0
    - httpx >= 0.27.0
    """
    import importlib.metadata

    requirements = {
        "restack-ai": "1.2.3",
        "pydantic": "2.7.0",
        "httpx": "0.27.0",
    }

    issues: list[str] = []

    for pkg_name, min_version in requirements.items():
        try:
            installed = importlib.metadata.version(pkg_name)
            # Simple version comparison (works for semantic versioning)
            installed_parts = tuple(int(x) for x in installed.split(".")[:3])
            min_parts = tuple(int(x) for x in min_version.split(".")[:3])

            if installed_parts < min_parts:
                issues.append(f"{pkg_name} {installed} (recommended >={min_version})")
        except importlib.metadata.PackageNotFoundError:
            issues.append(f"{pkg_name} not installed (recommended >={min_version})")
        except Exception:  # pragma: no cover - version parsing edge cases
            # Silently skip malformed versions
            pass

    if issues:
        return DoctorCheckResult(
            "package_versions",
            "warn",
            "Some packages below recommended versions",
            details="\n".join(f"  ! {issue}" for issue in issues),
        )

    return DoctorCheckResult("package_versions", "ok", "All package versions meet recommendations")


def check_project_structure(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Validate we're in a restack-gen project root or the library repo.

    Success criteria (any of):
    - A Python package directory named "restack_gen" (library repo)
    - A generated app with a pyproject.toml and a server/service.py
    """
    root = Path(base_dir).resolve()

    lib_pkg = root / "restack_gen"
    app_pyproject = root / "pyproject.toml"
    app_service = root / "server" / "service.py"

    if lib_pkg.exists() and lib_pkg.is_dir():
        return DoctorCheckResult("project_structure", "ok", "Found library package 'restack_gen'")

    if app_pyproject.exists() and app_service.exists():
        return DoctorCheckResult("project_structure", "ok", "Detected generated app structure")

    return DoctorCheckResult(
        "project_structure",
        "warn",
        "Not in a typical restack-gen project; some commands may be limited",
        details=str(root),
    )


def check_git_status(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Check git working tree cleanliness if inside a repo.

    Returns warn if repo is dirty, ok if clean or not a git repo.
    """
    root = Path(base_dir)
    try:
        # Determine if inside git repo
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0 or res.stdout.strip() != "true":
            return DoctorCheckResult("git", "ok", "Not a git repository (skipping)")

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        dirty = status.stdout.strip() != ""
        return DoctorCheckResult(
            "git",
            "warn" if dirty else "ok",
            "Git working tree is dirty" if dirty else "Git working tree is clean",
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        return DoctorCheckResult("git", "warn", "Unable to check git status", details=str(exc))


def check_write_permissions(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Check write permissions for key project directories.

    Validates write access to: src/, server/, client/, tests/
    """
    root = Path(base_dir)
    key_dirs = ["src", "server", "client", "tests"]
    issues: list[str] = []

    for dir_name in key_dirs:
        dir_path = root / dir_name
        # Only check if directory exists
        if dir_path.exists():
            if not os.access(dir_path, os.W_OK):
                issues.append(f"{dir_name}/ (no write access)")

    if issues:
        return DoctorCheckResult(
            "write_permissions",
            "fail",
            "Write permission denied for some directories",
            details="\n".join(f"  ✗ {issue}" for issue in issues),
        )

    return DoctorCheckResult("write_permissions", "ok", "Write access verified for key directories")


def check_restack_engine(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Check Restack engine connectivity.

    Attempts to connect to the Restack engine at the configured URL
    (default: http://localhost:7700 or from RESTACK_ENGINE_URL env var).

    Returns:
        ok: Engine is reachable
        warn: Non-critical connectivity issue
        fail: Engine unreachable or connection error
    """
    # Try to get engine URL from environment or config
    engine_url = os.environ.get("RESTACK_ENGINE_URL", "http://localhost:7700")

    # Try to load from settings if present
    try:
        settings_path = Path(base_dir) / "config" / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, encoding="utf-8") as f:
                settings = yaml.safe_load(f) or {}
                engine_url = settings.get("restack", {}).get("engine_url", engine_url)
    except Exception:
        # Silently fall back to default/env
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            # Try common health endpoints
            for path in ["/api/health", "/health", "/"]:
                try:
                    resp = client.get(f"{engine_url.rstrip('/')}{path}")
                    if resp.status_code < 500:
                        return DoctorCheckResult(
                            "restack_engine",
                            "ok",
                            f"Restack engine reachable at {engine_url}",
                        )
                except httpx.RequestError:
                    continue

            # If all paths fail, return connection error
            return DoctorCheckResult(
                "restack_engine",
                "fail",
                f"Restack engine not reachable at {engine_url}",
                details=(
                    "Fix: Ensure Restack engine is running.\n"
                    "  Start with: docker run -d -p 7700:7700 ghcr.io/restackio/engine:main\n"
                    "  Or set RESTACK_ENGINE_URL environment variable."
                ),
            )

    except Exception as exc:  # pragma: no cover - network errors
        return DoctorCheckResult(
            "restack_engine",
            "fail",
            f"Unable to connect to Restack engine at {engine_url}",
            details=f"Error: {exc}",
        )


def check_tools(base_dir: str | Path = ".", *, verbose: bool = False) -> DoctorCheckResult:
    """Check FastMCP tool servers configuration and health.

    Checks:
    - tools.yaml exists and is valid
    - FastMCP dependencies installed
    - Configured servers can be imported
    - Running servers are healthy (if service is running)

    Args:
        base_dir: Project root directory
        verbose: Include detailed server information

    Returns:
        DoctorCheckResult with tool server health status
    """
    root = Path(base_dir)
    tools_config = root / "config" / "tools.yaml"

    # Check if tools.yaml exists
    if not tools_config.exists():
        return DoctorCheckResult(
            "tools", "ok", "No tool servers configured (config/tools.yaml not found)"
        )

    try:
        # Load tools configuration
        with open(tools_config) as f:
            data = yaml.safe_load(f)

        if not data or "fastmcp" not in data:
            return DoctorCheckResult(
                "tools", "warn", "tools.yaml exists but has no fastmcp configuration"
            )

        servers = data["fastmcp"].get("servers", [])
        if not servers:
            return DoctorCheckResult(
                "tools", "warn", "tools.yaml exists but has no servers configured"
            )

        # Check if fastmcp is installed
        try:
            importlib.import_module("fastmcp")
        except ImportError:
            return DoctorCheckResult(
                "tools",
                "fail",
                f"FastMCP not installed (found {len(servers)} configured servers)",
                details="Run: pip install fastmcp",
            )

        # Check if each server module can be imported
        import_errors = []
        for server in servers:
            module_name = server.get("module", "")
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                import_errors.append(f"{server['name']}: {module_name} - {e}")

        if import_errors:
            return DoctorCheckResult(
                "tools",
                "fail",
                f"{len(import_errors)}/{len(servers)} tool servers cannot be imported",
                details="\n".join(import_errors),
            )

        # Try to get health status from running servers (async check)
        try:
            health_results = asyncio.run(_check_tools_health_async(root))

            running = sum(
                1 for h in health_results.values() if h.get("status") in ["healthy", "running"]
            )
            stopped = sum(1 for h in health_results.values() if h.get("status") == "stopped")
            errors = sum(1 for h in health_results.values() if h.get("status") == "error")

            if errors > 0:
                status: Status = "warn"
                msg = f"{errors}/{len(servers)} tool servers have errors"
            elif running == len(servers):
                status = "ok"
                msg = f"All {len(servers)} tool servers are running"
            elif stopped == len(servers):
                status = "ok"
                msg = f"All {len(servers)} tool servers configured (not running)"
            else:
                status = "warn"
                msg = f"{running}/{len(servers)} tool servers running, {stopped} stopped"

            if verbose:
                details = "\n".join(
                    f"  {name}: {info.get('status', 'unknown')}"
                    for name, info in health_results.items()
                )
            else:
                details = None

            return DoctorCheckResult("tools", status, msg, details=details)

        except Exception as e:
            # Health check failed, but config/imports are OK
            return DoctorCheckResult(
                "tools",
                "ok",
                f"{len(servers)} tool servers configured and importable",
                details=f"Health check unavailable: {e}",
            )

    except yaml.YAMLError as e:
        return DoctorCheckResult(
            "tools", "fail", "tools.yaml contains invalid YAML", details=str(e)
        )
    except Exception as e:
        return DoctorCheckResult("tools", "warn", "Unable to check tool servers", details=str(e))


def _load_llm_config(base_dir: str | Path = ".") -> dict[str, Any] | None:
    """Load LLM router YAML config if present.

    Returns parsed dict or None if file missing/invalid.
    """
    path = Path(base_dir) / "config" / "llm_router.yaml"
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return cast(dict[str, Any], yaml.safe_load(f) or {})
    except Exception:
        return None


def check_llm_config(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Validate LLM router configuration and provider credentials.

    Checks:
    - config/llm_router.yaml exists and parses
    - providers list is present and non-empty
    - required environment variables referenced in api_key/base_url are set
    """
    cfg = _load_llm_config(base_dir)
    if cfg is None:
        return DoctorCheckResult(
            "llm_config",
            "warn",
            "LLM router config not found (config/llm_router.yaml)",
            details="Fix: run 'restack g llm-config' to scaffold default configuration.",
        )

    llm = cast(dict[str, Any] | None, cfg.get("llm"))
    if not llm:
        return DoctorCheckResult(
            "llm_config",
            "fail",
            "config/llm_router.yaml missing 'llm' root key",
            details="Fix: regenerate with 'restack g llm-config' or update the YAML structure.",
        )

    providers = cast(list[dict[str, Any]] | None, llm.get("providers"))
    if not providers:
        return DoctorCheckResult(
            "llm_config",
            "fail",
            "No providers configured under llm.providers",
            details="Fix: add at least one provider entry (e.g., OpenAI) and set its API key.",
        )

    # Scan for ${ENV_VAR} and ${ENV_VAR:-default} patterns in string fields
    missing_env: set[str] = set()

    env_pattern = re.compile(r"\$\{([A-Z0-9_]+)(?::-[^}]*)?\}")

    def _collect_env_refs(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                _collect_env_refs(v)
        elif isinstance(obj, list):
            for v in obj:
                _collect_env_refs(v)
        elif isinstance(obj, str):
            for m in env_pattern.finditer(obj):
                var = m.group(1)
                if var and var not in os.environ:
                    missing_env.add(var)

    _collect_env_refs(providers)
    _collect_env_refs(llm.get("router", {}))

    if missing_env:
        exports = "\n".join(f"  export {var}=..." for var in sorted(missing_env))
        return DoctorCheckResult(
            "llm_config",
            "warn",
            f"Missing environment variables for LLM config: {', '.join(sorted(missing_env))}",
            details=f"Fix: set the following environment variables before running:\n{exports}",
        )

    return DoctorCheckResult("llm_config", "ok", "LLM router config and env look good")


def check_kong_gateway(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Check Kong AI Gateway reachability if configured as backend.

    Attempts a quick GET request to the configured router URL. Any HTTP status response
    indicates basic reachability; connection/timeout errors are considered failures.
    """
    cfg = _load_llm_config(base_dir)
    if cfg is None:
        return DoctorCheckResult("kong", "ok", "Kong not checked (llm config missing)")

    llm = cast(dict[str, Any] | None, cfg.get("llm")) or {}
    router = cast(dict[str, Any] | None, llm.get("router")) or {}
    backend = str(router.get("backend", "direct"))
    if backend != "kong":
        return DoctorCheckResult("kong", "ok", "Kong not configured (backend=direct)")

    url = str(router.get("url", "http://localhost:8000")).rstrip("/")
    timeout_val = float(router.get("timeout", 5))

    try:
        with httpx.Client(timeout=timeout_val) as client:
            # A simple GET to root; any non-network error response counts as reachable
            resp = client.get(url)
            return DoctorCheckResult(
                "kong",
                "ok" if resp.status_code < 500 else "warn",
                f"Kong reachable at {url} (status {resp.status_code})",
            )
    except httpx.RequestError as exc:
        return DoctorCheckResult(
            "kong",
            "fail",
            f"Kong gateway not reachable at {url}",
            details=(
                "Fix: ensure Kong is running and KONG_GATEWAY_URL is set.\n"
                f"Tried GET {url} • Error: {exc}"
            ),
        )


def check_prompts(base_dir: str | Path = ".") -> DoctorCheckResult:
    """Validate prompts registry and referenced files exist.

    Checks:
    - config/prompts.yaml exists and parses
    - Each prompt has a 'latest' version
    - Each referenced file exists on disk
    """
    cfg_path = Path(base_dir) / "config" / "prompts.yaml"
    if not cfg_path.exists():
        return DoctorCheckResult(
            "prompts",
            "warn",
            "No prompts registry found (config/prompts.yaml)",
            details="Fix: restack g prompt MyPrompt --version 1.0.0",
        )

    try:
        data = cast(dict[str, Any], yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {})
    except yaml.YAMLError as e:
        return DoctorCheckResult(
            "prompts", "fail", "prompts.yaml contains invalid YAML", details=str(e)
        )

    prompts = cast(dict[str, Any] | None, data.get("prompts")) or {}
    if not prompts:
        return DoctorCheckResult("prompts", "warn", "No prompts defined in prompts.yaml")

    missing_files: list[str] = []
    missing_latest: list[str] = []
    for name, cfg in prompts.items():
        versions = cast(dict[str, str] | None, cfg.get("versions")) or {}
        latest = cast(str | None, cfg.get("latest"))
        if not latest:
            missing_latest.append(name)
        if versions:
            for v, path in versions.items():
                p = Path(path)
                if not p.exists():
                    missing_files.append(f"{name}@{v}: {path}")

    if missing_files or missing_latest:
        details_lines: list[str] = []
        if missing_latest:
            details_lines.append("Missing 'latest' for: " + ", ".join(sorted(missing_latest)))
        if missing_files:
            details_lines.append("Missing prompt files:\n  " + "\n  ".join(missing_files))
        details_lines.append("Fix: create the missing files or update paths in config/prompts.yaml")
        return DoctorCheckResult(
            "prompts",
            "warn",
            "Some prompts are misconfigured or files are missing",
            details="\n".join(details_lines),
        )

    return DoctorCheckResult("prompts", "ok", "Prompts registry is valid")


async def _check_tools_health_async(base_dir: Path) -> dict[str, dict[str, Any]]:
    """Async helper to check tool server health.

    Args:
        base_dir: Project root directory

    Returns:
        Dict mapping server names to health status
    """
    try:
        # Change to project directory for imports
        import os

        original_cwd = os.getcwd()
        os.chdir(base_dir)

        # Add project to path if needed
        if str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))

        try:
            # Import the manager from the project
            # Use dynamic import to avoid circular dependencies
            manager_module = None
            for subdir in base_dir.iterdir():
                if subdir.is_dir() and (subdir / "common" / "fastmcp_manager.py").exists():
                    module_path = f"{subdir.name}.common.fastmcp_manager"
                    manager_module = importlib.import_module(module_path)
                    break

            if manager_module is None:
                return {}

            # Get manager and check health
            manager_class = manager_module.FastMCPServerManager
            manager = manager_class()
            health_results = cast(dict[str, dict[str, Any]], await manager.health_check_all())

            return health_results
        finally:
            os.chdir(original_cwd)

    except Exception:
        # Silently fail - health check is optional
        return {}


def run_all_checks(
    base_dir: str | Path = ".", *, verbose: bool = False, check_tools_flag: bool = False
) -> list[DoctorCheckResult]:
    """Run all doctor checks and return individual results.

    Args:
        base_dir: Project root directory
        verbose: Include detailed information in results
        check_tools_flag: Whether to include tool server health checks

    Returns:
        List of check results
    """
    checks: list[DoctorCheckResult] = []

    # Core environment checks
    checks.append(check_python_version())
    checks.append(check_dependencies())
    checks.append(check_package_versions())
    checks.append(check_project_structure(base_dir))
    checks.append(check_write_permissions(base_dir))
    checks.append(check_git_status(base_dir))

    # Restack engine connectivity (critical v1.0 check)
    checks.append(check_restack_engine(base_dir))

    # V2 configuration checks (LLM, prompts, tools)
    checks.append(check_llm_config(base_dir))
    checks.append(check_kong_gateway(base_dir))
    checks.append(check_prompts(base_dir))

    if check_tools_flag:
        checks.append(check_tools(base_dir, verbose=verbose))

    return checks


def summarize(results: Iterable[DoctorCheckResult]) -> dict[str, int | Status]:
    """Summarize results and compute an overall status.

    Returns a dict with keys: ok, warn, fail, overall
    """
    counts_int: dict[str, int] = {"ok": 0, "warn": 0, "fail": 0}
    worst: Status = "ok"
    for r in results:
        counts_int[r.status] += 1
        if _status_priority(r.status) > _status_priority(worst):
            worst = r.status
    result: dict[str, int | Status] = {**counts_int, "overall": worst}
    return result
```

---

## restack_gen\generator.py

<a id="restack_gen-generator-py"></a>

**File:** `restack_gen\generator.py`

```python
"""Resource generation utilities for agents, workflows, and functions."""

import re
from pathlib import Path
from typing import Any

from restack_gen.ast_service import update_service_file
from restack_gen.codegen import generate_pipeline_code
from restack_gen.renderer import render_template


class GenerationError(Exception):
    """Raised when resource generation fails."""


GENERATED_MARKER = "# @generated by restack-gen"


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case.

    Args:
        name: Input name

    Returns:
        snake_case version
    """
    # Insert underscore before uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase letters preceded by lowercase
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def to_pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase.

    Args:
        name: Input name in snake_case

    Returns:
        PascalCase version
    """
    parts = name.split("_")
    return "".join(word.capitalize() for word in parts)


def validate_name(name: str) -> tuple[bool, str | None]:
    """Validate resource name.

    Args:
        name: Resource name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"

    # Check for valid identifier characters
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return (
            False,
            "Name must start with letter/underscore and contain only alphanumeric characters and underscores",
        )

    return True, None


def find_project_root() -> Path | None:
    """Find the project root by looking for pyproject.toml.

    Returns:
        Path to project root, or None if not found
    """
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def get_project_name(project_root: Path) -> str:
    """Extract project name from pyproject.toml.

    Args:
        project_root: Path to project root

    Returns:
        Project name

    Raises:
        GenerationError: If project name cannot be determined
    """
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        raise GenerationError("pyproject.toml not found")

    with open(pyproject, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("name = "):
                # Extract name from 'name = "myproject"'
                name = line.split("=")[1].strip().strip('"').strip("'")
                return name

    raise GenerationError("Could not find project name in pyproject.toml")


def check_file_exists(file_path: Path, force: bool = False) -> None:
    """Check if file exists and handle according to force flag.

    Args:
        file_path: Path to check
        force: If True, allow overwriting

    Raises:
        GenerationError: If file exists and cannot be overwritten
    """
    if not file_path.exists():
        return

    # Check if file has generated marker
    with open(file_path, encoding="utf-8") as f:
        first_line = f.readline()

    if GENERATED_MARKER in first_line:
        if not force:
            raise GenerationError(
                f"File {file_path} already exists (generated). Use --force to overwrite."
            )
    else:
        raise GenerationError(
            f"File {file_path} exists but was not generated by restack-gen. "
            "Will not overwrite to preserve manual changes."
        )


def write_file(file_path: Path, content: str) -> None:
    """Write content to file, creating directories if needed.

    Args:
        file_path: Path to write to
        content: Content to write
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def _read_yaml(file_path: Path) -> dict[str, Any]:
    """Read a YAML file into a dict, returning empty dict if missing.

    Args:
        file_path: YAML file path

    Returns:
        Dict parsed from YAML or empty dict if file doesn't exist
    """
    import yaml

    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(file_path: Path, data: dict[str, Any]) -> None:
    """Write a dict to YAML file with safe formatting."""
    import re

    import yaml

    # Use a custom dumper that quotes only semver-like strings and prompt file paths
    class SemverQuotedDumper(yaml.SafeDumper):
        pass

    def _conditional_str_representer(
        dumper: SemverQuotedDumper, value: str
    ) -> "yaml.nodes.Node":  # types from PyYAML
        if re.match(r"^\d+\.\d+\.\d+$", value) or value.startswith("prompts/"):
            return dumper.represent_scalar("tag:yaml.org,2002:str", value, style='"')
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)

    SemverQuotedDumper.add_representer(str, _conditional_str_representer)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, Dumper=SemverQuotedDumper)


def generate_agent(
    name: str,
    force: bool = False,
    event_type: str = "dict",
    state_type: str = "dict",
    with_llm: bool = False,
    tools_server: str | None = None,
) -> dict[str, Path]:
    """Generate an agent with test and client files.

    Args:
        name: Agent name (will be converted to PascalCase for class name)
        force: If True, overwrite existing generated files
        event_type: Type for agent events
        state_type: Type for agent state
        with_llm: If True, include LLM router and prompt loader
        tools_server: FastMCP tool server name to integrate

    Returns:
        Dictionary mapping file type to path

    Raises:
        GenerationError: If generation fails
    """
    # Validate name
    is_valid, error = validate_name(name)
    if not is_valid:
        raise GenerationError(f"Invalid agent name: {error}")

    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Convert name formats - ensure PascalCase
    if "_" in name:
        # snake_case input
        class_name = to_pascal_case(name) + "Agent"
        module_name = name
    else:
        # Assume PascalCase input
        class_name = name if name.endswith("Agent") else name + "Agent"
        # Ensure first letter is uppercase for PascalCase
        class_name = class_name[0].upper() + class_name[1:]
        # Extract base name without "Agent" suffix for module
        base_name = class_name.replace("Agent", "")
        module_name = to_snake_case(base_name)

    # Define file paths
    agent_file = project_root / "src" / project_name / "agents" / f"{module_name}.py"
    test_file = project_root / "tests" / f"test_{module_name}_agent.py"
    client_file = project_root / "client" / f"schedule_{module_name}.py"
    service_file = project_root / "server" / "service.py"

    # Check if files exist
    check_file_exists(agent_file, force)
    check_file_exists(test_file, force)
    check_file_exists(client_file, force)

    # Prepare context
    context = {
        "project_name": project_name,
        "agent_name": class_name,
        "name": class_name,  # For template compatibility
        "event_enum_name": f"{class_name}Event",
        "module_name": module_name,
        "event_type": event_type,
        "state_type": state_type,
        "events": [],  # Empty list for now, user can add events
        "state_fields": [],  # Empty list for now, user can add state fields
        "with_llm": with_llm,
        "tools_server": tools_server,
    }

    # Generate agent file
    agent_content = render_template("agent.py.j2", context)
    write_file(agent_file, agent_content)

    # Generate test file
    test_content = render_template("test_agent.py.j2", context)
    write_file(test_file, test_content)

    # Generate client file
    client_content = render_template("client_schedule_agent.py.j2", context)
    write_file(client_file, client_content)

    # Update service.py
    update_service_file(service_file, "agent", module_name, class_name)

    return {
        "agent": agent_file,
        "test": test_file,
        "client": client_file,
    }


def generate_workflow(
    name: str,
    force: bool = False,
    input_type: str = "dict",
    output_type: str = "dict",
) -> dict[str, Path]:
    """Generate a workflow with test and client files.

    Args:
        name: Workflow name (will be converted to PascalCase for class name)
        force: If True, overwrite existing generated files
        input_type: Type for workflow input
        output_type: Type for workflow output

    Returns:
        Dictionary mapping file type to path

    Raises:
        GenerationError: If generation fails
    """
    # Validate name
    is_valid, error = validate_name(name)
    if not is_valid:
        raise GenerationError(f"Invalid workflow name: {error}")

    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Convert name formats - ensure PascalCase
    if "_" in name:
        # snake_case input
        class_name = to_pascal_case(name) + "Workflow"
        module_name = name
    else:
        # Assume PascalCase input
        class_name = name if name.endswith("Workflow") else name + "Workflow"
        # Ensure first letter is uppercase for PascalCase
        class_name = class_name[0].upper() + class_name[1:]
        # Extract base name without "Workflow" suffix for module
        base_name = class_name.replace("Workflow", "")
        module_name = to_snake_case(base_name)

    # Define file paths
    workflow_file = project_root / "src" / project_name / "workflows" / f"{module_name}.py"
    test_file = project_root / "tests" / f"test_{module_name}_workflow.py"
    client_file = project_root / "client" / f"run_{module_name}.py"
    service_file = project_root / "server" / "service.py"

    # Check if files exist
    check_file_exists(workflow_file, force)
    check_file_exists(test_file, force)
    check_file_exists(client_file, force)

    # Prepare context
    context = {
        "project_name": project_name,
        "workflow_name": class_name,
        "name": class_name,  # For template compatibility
        "module_name": module_name,
        "input_type": input_type,
        "output_type": output_type,
        "input_fields": [],  # Empty list for now, user can customize
        "output_fields": [],  # Empty list for now, user can customize
    }

    # Generate workflow file
    workflow_content = render_template("workflow.py.j2", context)
    write_file(workflow_file, workflow_content)

    # Generate test file
    test_content = render_template("test_workflow.py.j2", context)
    write_file(test_file, test_content)

    # Generate client file
    client_content = render_template("client_run_workflow.py.j2", context)
    write_file(client_file, client_content)

    # Update service.py
    update_service_file(service_file, "workflow", module_name, class_name)

    return {
        "workflow": workflow_file,
        "test": test_file,
        "client": client_file,
    }


def generate_function(
    name: str,
    force: bool = False,
) -> dict[str, Path]:
    """Generate a function with test file.

    Args:
        name: Function name (should be in snake_case)
        force: If True, overwrite existing generated files

    Returns:
        Dictionary mapping file type to path

    Raises:
        GenerationError: If generation fails
    """
    # Validate name
    is_valid, error = validate_name(name)
    if not is_valid:
        raise GenerationError(f"Invalid function name: {error}")

    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Convert to snake_case if needed
    function_name = to_snake_case(name) if any(c.isupper() for c in name) else name

    # Define file paths
    function_file = project_root / "src" / project_name / "functions" / f"{function_name}.py"
    test_file = project_root / "tests" / f"test_{function_name}_function.py"
    service_file = project_root / "server" / "service.py"

    # Check if files exist
    check_file_exists(function_file, force)
    check_file_exists(test_file, force)

    # Prepare context
    context = {
        "project_name": project_name,
        "function_name": function_name,
    }

    # Generate function file
    function_content = render_template("function.py.j2", context)
    write_file(function_file, function_content)

    # Generate test file
    test_content = render_template("test_function.py.j2", context)
    write_file(test_file, test_content)

    # Update service.py
    update_service_file(service_file, "function", function_name, function_name)

    return {
        "function": function_file,
        "test": test_file,
    }


def generate_pipeline(
    name: str,
    operators: str,
    force: bool = False,
) -> dict[str, Path]:
    """Generate a pipeline from operator expression.

    Args:
        name: Pipeline name (will be converted to PascalCase for class name)
        operators: Operator expression (e.g., "A → B ⇄ C")
        force: If True, overwrite existing generated files

    Returns:
        Dictionary mapping file type to path

    Raises:
        GenerationError: If generation fails
    """
    # Validate name
    is_valid, error = validate_name(name)
    if not is_valid:
        raise GenerationError(f"Invalid pipeline name: {error}")

    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Parse and validate operator expression (import locally to avoid circular import)
    try:
        from restack_gen.parser import parse_and_validate

        ir = parse_and_validate(operators)
    except Exception as e:
        raise GenerationError(f"Failed to parse operator expression: {e}") from e

    # Validate pipeline structure
    try:
        from restack_gen.validator import validate_pipeline

        validation = validate_pipeline(ir, strict=False)

        if not validation.is_valid:
            error_details = "\n  - ".join(validation.errors)
            raise GenerationError(f"Pipeline validation failed:\n  - {error_details}")

        # Show warnings if any
        if validation.warnings:
            import warnings

            for warning in validation.warnings:
                warnings.warn(warning, UserWarning, stacklevel=2)

    except GenerationError:
        raise
    except Exception as e:
        raise GenerationError(f"Failed to validate pipeline: {e}") from e

    # Generate names
    workflow_name = to_snake_case(name)
    pipeline_name = to_pascal_case(workflow_name)
    if not pipeline_name.endswith("Workflow"):
        pipeline_name += "Workflow"

    # Define file paths
    workflow_file = (
        project_root / "src" / project_name / "workflows" / f"{workflow_name}_workflow.py"
    )
    test_file = project_root / "tests" / f"test_{workflow_name}_workflow.py"
    service_file = project_root / "server" / "service.py"

    # Check if files exist
    check_file_exists(workflow_file, force)
    check_file_exists(test_file, force)

    # Generate workflow code using codegen
    workflow_content = generate_pipeline_code(ir, pipeline_name, project_name)
    workflow_content = GENERATED_MARKER + "\n" + workflow_content

    # Write workflow file
    write_file(workflow_file, workflow_content)

    # Generate test file
    context = {
        "project_name": project_name,
        "workflow_name": workflow_name,
        "class_name": pipeline_name,
    }
    test_content = render_template("test_workflow.py.j2", context)
    write_file(test_file, test_content)

    # Update service.py
    update_service_file(
        service_file,
        "workflow",
        f"{workflow_name}_workflow",
        pipeline_name,
    )

    return {
        "workflow": workflow_file,
        "test": test_file,
    }


def generate_llm_config(
    force: bool = False,
    backend: str = "direct",
) -> dict[str, Path]:
    """Generate LLM router configuration files.

    Args:
        force: If True, overwrite existing files
        backend: Backend type ("direct" or "kong")

    Returns:
        Dictionary mapping file type to path

    Raises:
        GenerationError: If generation fails
    """
    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Define file paths
    config_dir = project_root / "config"
    config_file = config_dir / "llm_router.yaml"
    common_dir = project_root / "src" / project_name / "common"
    llm_router_file = common_dir / "llm_router.py"
    observability_file = common_dir / "observability.py"

    # Check if files exist
    if config_file.exists() and not force:
        raise GenerationError(
            f"Config file {config_file} already exists. Use --force to overwrite."
        )

    if llm_router_file.exists() and not force:
        raise GenerationError(f"File {llm_router_file} already exists. Use --force to overwrite.")

    # Prepare context
    context = {
        "backend": backend,
    }

    # Generate config file
    config_content = render_template("llm_router.yaml.j2", context)
    write_file(config_file, config_content)

    # Generate LLM router module
    router_content = render_template("llm_router.py.j2", context)
    write_file(llm_router_file, router_content)

    # Generate observability helpers (idempotent; overwrite only with force)
    if not observability_file.exists() or force:
        observability_content = render_template("observability.py.j2", {})
        write_file(observability_file, observability_content)

    # Create __init__.py in common if it doesn't exist
    init_file = common_dir / "__init__.py"
    if not init_file.exists():
        write_file(init_file, '"""Common utilities and shared components."""\n')

    return {
        "config": config_file,
        "router": llm_router_file,
        "observability": observability_file,
    }


def generate_prompt(
    name: str,
    version: str = "1.0.0",
    force: bool = False,
) -> dict[str, Path]:
    """Generate a versioned prompt markdown file and update the prompt registry.

    Creates/updates config/prompts.yaml and ensures a prompt loader exists.

    Args:
        name: Prompt name (PascalCase or snake_case). Stored as snake_case key.
        version: Semantic version (e.g., 1.0.0). Determines file path.
        force: Overwrite existing prompt version file if set.

    Returns:
        Dict with paths: {'prompt', 'config', 'loader' (optional)}
    """
    # Validate name
    is_valid, error = validate_name(name)
    if not is_valid:
        raise GenerationError(f"Invalid prompt name: {error}")

    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Normalize key and file locations
    prompt_key = to_snake_case(name)
    config_file = project_root / "config" / "prompts.yaml"
    prompt_dir = project_root / "prompts" / prompt_key
    prompt_file = prompt_dir / f"v{version}.md"
    common_dir = project_root / "src" / project_name / "common"
    loader_file = common_dir / "prompt_loader.py"

    # Check overwrite policy for prompt file
    if prompt_file.exists() and not force:
        # Even though prompt files are user-editable, we guard accidental overwrite
        raise GenerationError(
            f"Prompt version file {prompt_file} already exists. Use --force to overwrite."
        )

    # Ensure prompt loader exists (generate if missing)
    loader_generated = False
    if not loader_file.exists():
        import datetime as _dt
        from importlib.metadata import version as _pkg_version

        try:
            gen_version = _pkg_version("restack-gen")
        except Exception:
            gen_version = "unknown"

        loader_content = render_template(
            "prompt_loader.py.j2",
            {
                "version": gen_version,
                "timestamp": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        write_file(loader_file, loader_content)
        # create __init__ in common if absent
        init_file = common_dir / "__init__.py"
        if not init_file.exists():
            write_file(init_file, '"""Common utilities and shared components."""\n')
        loader_generated = True

    # Render prompt markdown from template
    prompt_md = render_template(
        "prompt_template.md.j2",
        {
            "version": version,
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 4096,
            "name": prompt_key,
        },
    )
    write_file(prompt_file, prompt_md)

    # Update registry YAML
    registry = _read_yaml(config_file)
    if "prompts" not in registry:
        registry["prompts"] = {}
    entry = registry["prompts"].get(prompt_key) or {
        "description": f"Prompt for {prompt_key.replace('_', ' ')}",
        "versions": {},
        "latest": version,
        "resolution": "semver",
    }
    # Add/overwrite mapping for version to file path
    rel_path = f"prompts/{prompt_key}/v{version}.md"
    entry.setdefault("versions", {})[version] = rel_path

    # Update 'latest' if the incoming version is greater (lexicographic fallback to simple semver compare)
    def _parse(v: str) -> tuple[int, int, int]:
        try:
            major, minor, patch = v.split(".")
            return (int(major), int(minor), int(patch))
        except Exception:
            return (0, 0, 0)

    try:
        if _parse(version) >= _parse(entry.get("latest", "0.0.0")):
            entry["latest"] = version
    except Exception:
        # Best effort; keep existing latest if parsing failed
        pass

    registry["prompts"][prompt_key] = entry
    _write_yaml(config_file, registry)

    result: dict[str, Path] = {
        "prompt": prompt_file,
        "config": config_file,
    }
    if loader_generated:
        result["loader"] = loader_file
    return result


def generate_tool_server(
    name: str,
    force: bool = False,
) -> dict[str, Path]:
    """Generate a FastMCP tool server with configuration.

    Args:
        name: Tool server name (will be converted to PascalCase for class name)
        force: If True, overwrite existing generated files

    Returns:
        Dictionary mapping file type to path ('config', 'server')

    Raises:
        GenerationError: If generation fails
    """
    # Validate name
    is_valid, error = validate_name(name)
    if not is_valid:
        raise GenerationError(f"Invalid tool server name: {error}")

    # Find project root
    project_root = find_project_root()
    if not project_root:
        raise GenerationError(
            "Not in a restack-gen project. Run this command from within a project directory."
        )

    project_name = get_project_name(project_root)

    # Convert name formats
    if "_" in name:
        # snake_case input
        class_name = to_pascal_case(name)
        module_name = name
    else:
        # Assume PascalCase input
        class_name = name
        module_name = to_snake_case(name)

    # Generate server name (lowercase, underscores)
    server_name = f"{module_name}_tools"

    # Define file paths
    config_dir = project_root / "config"
    config_file = config_dir / "tools.yaml"
    tools_dir = project_root / "src" / project_name / "tools"
    server_file = tools_dir / f"{module_name}_mcp.py"
    tools_init = tools_dir / "__init__.py"
    common_dir = project_root / "src" / project_name / "common"
    manager_file = common_dir / "fastmcp_manager.py"
    observability_file = common_dir / "observability.py"

    # Check if files exist
    if server_file.exists() and not force:
        raise GenerationError(
            f"Tool server {server_file} already exists. Use --force to overwrite."
        )

    # Prepare context
    import datetime

    context = {
        "name": class_name,
        "project_name": project_name,
        "module_name": module_name,
        "module_file_name": f"{module_name}_mcp",  # For import paths in config
        "server_name": server_name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Generate tool server file
    server_content = render_template("tool_server.py.j2", context)
    write_file(server_file, server_content)

    # Generate or update config file
    if config_file.exists() and not force:
        # Config exists, don't overwrite
        print(f"Config file {config_file} already exists. Skipping config generation.")
        print("Add this server manually to your tools.yaml configuration.")
    else:
        config_content = render_template("tools.yaml.j2", context)
        write_file(config_file, config_content)

    # Create __init__.py in tools directory if it doesn't exist
    if not tools_init.exists():
        write_file(tools_init, '"""FastMCP tool servers for agent capabilities."""\n')

    # Ensure observability helpers exist (idempotent)
    if not observability_file.exists() or force:
        try:
            observability_content = render_template("observability.py.j2", {})
            write_file(observability_file, observability_content)
        except Exception:
            # Best effort; manager generation may still proceed
            pass

    # Generate FastMCP manager if this is the first tool server
    manager_generated = False
    if not manager_file.exists():
        try:
            from importlib.metadata import version

            gen_version = version("restack-gen")
        except Exception:
            gen_version = "unknown"

        manager_context = {
            "version": gen_version,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        manager_content = render_template("fastmcp_manager.py.j2", manager_context)
        write_file(manager_file, manager_content)
        print(f"Generated FastMCP manager: {manager_file}")
        manager_generated = True

    result: dict[str, Path] = {
        "server": server_file,
    }
    # Only include keys when a file was generated/overwritten to keep values as Path (not None)
    if not config_file.exists() or force:
        result["config"] = config_file
    if manager_generated:
        result["manager"] = manager_file
    return result
```

---

## restack_gen\ir.py

<a id="restack_gen-ir-py"></a>

**File:** `restack_gen\ir.py`

```python
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
```

---

## restack_gen\parser.py

<a id="restack_gen-parser-py"></a>

**File:** `restack_gen\parser.py`

```python
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


def validate_ir(ir: IRNode, project_root: Path | None = None) -> tuple[bool, str | None]:
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
    try:
        resources = get_project_resources()
    except RuntimeError as e:
        return False, str(e)

    def validate_node(node: IRNode) -> tuple[bool, str | None]:
        """Recursively validate a node."""
        if isinstance(node, Resource):
            # Check if resource exists
            if node.resource_type == "unknown":
                # Try to determine type from project
                if node.name not in resources:
                    return False, f"Resource '{node.name}' not found in project"
                # Update resource type
                node.resource_type = resources[node.name]
            else:
                # Validate type matches
                if node.name not in resources:
                    return False, f"Resource '{node.name}' not found in project"
                if resources[node.name] != node.resource_type:
                    return (
                        False,
                        f"Resource '{node.name}' is a {resources[node.name]}, "
                        f"not a {node.resource_type}",
                    )
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
```

---

## restack_gen\project.py

<a id="restack_gen-project-py"></a>

**File:** `restack_gen\project.py`

```python
"""Project generation utilities for creating new Restack applications."""

import re
from pathlib import Path
from typing import Any

from restack_gen.renderer import render_template


def validate_project_name(name: str) -> tuple[bool, str]:
    """Validate project name follows naming conventions.

    Project names must:
    - Contain only lowercase letters, numbers, and underscores
    - Start with a letter
    - Not be a Python keyword or reserved word

    Args:
        name: The project name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if empty
    if not name:
        return False, "Project name cannot be empty"

    # Check pattern: lowercase letters, numbers, underscores only, must start with letter
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return (
            False,
            "Project name must start with a letter and contain only lowercase letters, numbers, and underscores",
        )

    # Check for Python keywords
    import keyword

    if keyword.iskeyword(name):
        return False, f"'{name}' is a Python keyword and cannot be used as a project name"

    # Check for common reserved words
    reserved = {"test", "tests", "src", "lib", "bin", "dist", "build", "venv"}
    if name in reserved:
        return False, f"'{name}' is a reserved word and cannot be used as a project name"

    return True, ""


def create_project_structure(project_path: Path, project_name: str) -> None:
    """Create the directory structure for a new Restack project.

    Args:
        project_path: Root path where the project will be created
        project_name: Name of the project (used for src directory)
    """
    directories = [
        project_path / "config",
        project_path / "server",
        project_path / "client",
        project_path / "src" / project_name,
        project_path / "src" / project_name / "agents",
        project_path / "src" / project_name / "workflows",
        project_path / "src" / project_name / "functions",
        project_path / "src" / project_name / "common",
        project_path / "tests",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def generate_project_files(project_path: Path, project_name: str) -> None:
    """Generate all project files from templates.

    Args:
        project_path: Root path of the project
        project_name: Name of the project
    """
    context = {
        "project_name": project_name,
        "version": "0.1.0",
        "description": f"Restack application: {project_name}",
        "task_queue": project_name,
        "env_prefix": project_name.upper(),
        "command": f"restack new {project_name}",
    }

    # Generate root-level configuration files
    _write_template(project_path / "pyproject.toml", "pyproject.toml.j2", context)
    _write_template(project_path / "Makefile", "Makefile.j2", context)
    _write_template(project_path / ".gitignore", ".gitignore.j2", context)
    _write_template(project_path / "README.md", "README.md.j2", context)

    # Generate config files
    _write_template(project_path / "config" / "settings.yaml", "settings.yaml.j2", context)
    _write_template(project_path / "config" / ".env.example", ".env.example.j2", context)

    # Generate common modules
    common_dir = project_path / "src" / project_name / "common"
    _write_template(common_dir / "retries.py", "retries.py.j2", context)
    _write_template(common_dir / "settings.py", "settings.py.j2", context)
    _write_template(common_dir / "compat.py", "compat.py.j2", context)
    _write_template(common_dir / "__init__.py", None, context)  # Empty __init__.py

    # Generate empty service.py (no resources yet)
    service_context = {
        **context,
        "agents": [],
        "workflows": [],
        "functions": [],
    }
    _write_template(project_path / "server" / "service.py", "service.py.j2", service_context)

    # Generate __init__.py files for package structure
    src_root = project_path / "src" / project_name
    for subdir in ["agents", "workflows", "functions"]:
        _write_template(src_root / subdir / "__init__.py", None, context)

    _write_template(src_root / "__init__.py", None, context)


def _write_template(file_path: Path, template_name: str | None, context: dict[str, Any]) -> None:
    """Write a rendered template to a file.

    Args:
        file_path: Path where the file will be written
        template_name: Name of the template file (None for empty files)
        context: Template context variables
    """
    if template_name is None:
        # Create empty file
        file_path.write_text("", encoding="utf-8")
    else:
        content = render_template(template_name, context)
        file_path.write_text(content, encoding="utf-8")


def create_new_project(
    project_name: str, parent_dir: Path | None = None, force: bool = False
) -> Path:
    """Create a new Restack project with complete structure.

    Args:
        project_name: Name of the project to create
        parent_dir: Parent directory (defaults to current directory)
        force: If True, overwrite existing directory

    Returns:
        Path to the created project

    Raises:
        ValueError: If project name is invalid
        FileExistsError: If project directory already exists and force=False
    """
    # Validate project name
    is_valid, error_message = validate_project_name(project_name)
    if not is_valid:
        raise ValueError(error_message)

    # Determine project path
    parent = parent_dir or Path.cwd()
    project_path = parent / project_name

    # Check if directory exists
    if project_path.exists() and not force:
        raise FileExistsError(
            f"Directory '{project_name}' already exists. Use --force to overwrite."
        )

    # Create project structure
    create_project_structure(project_path, project_name)

    # Generate all project files
    generate_project_files(project_path, project_name)

    return project_path
```

---

## restack_gen\renderer.py

<a id="restack_gen-renderer-py"></a>

**File:** `restack_gen\renderer.py`

```python
"""Template rendering engine for restack-gen.

This module provides utilities for rendering Jinja2 templates with common context
and proper timestamp generation.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from restack_gen import __version__


class TemplateRenderer:
    """Renders Jinja2 templates with common context."""

    def __init__(self) -> None:
        """Initialize the template renderer with Jinja2 environment."""
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render_template(self, template_name: str, context: dict[str, Any] | None = None) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of the template file (e.g., 'agent.py.j2')
            context: Template variables to pass to the template

        Returns:
            Rendered template as a string
        """
        template = self.env.get_template(template_name)
        full_context = self._build_context(context or {})
        return template.render(**full_context)

    def _build_context(self, user_context: dict[str, Any]) -> dict[str, Any]:
        """Build the full template context with common variables.

        Args:
            user_context: User-provided template variables

        Returns:
            Complete context dictionary with common variables added
        """
        common_context = {
            "generator_version": __version__,
            "timestamp": self._get_timestamp(),
        }
        # User context takes precedence over common context
        return {**common_context, **user_context}

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format.

        Returns:
            ISO 8601 formatted timestamp string
        """
        return datetime.now(UTC).isoformat()


# Singleton instance for convenience
_renderer = TemplateRenderer()


def render_template(template_name: str, context: dict[str, Any] | None = None) -> str:
    """Convenience function to render a template.

    Args:
        template_name: Name of the template file (e.g., 'agent.py.j2')
        context: Template variables to pass to the template

    Returns:
        Rendered template as a string
    """
    return _renderer.render_template(template_name, context)
```

---

## restack_gen\runner.py

<a id="restack_gen-runner-py"></a>

**File:** `restack_gen\runner.py`

```python
"""Service runner for starting Restack applications.

This module provides utilities for running generated Restack services
with proper environment setup and graceful shutdown handling.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


class RunnerError(Exception):
    """Raised when service runner encounters an error."""

    pass


def find_service_file(base_dir: str | Path = ".") -> Path:
    """Locate server/service.py in the project structure.

    Args:
        base_dir: Base directory to search from

    Returns:
        Path to service.py

    Raises:
        RunnerError: If service.py cannot be found
    """
    root = Path(base_dir).resolve()
    service_path = root / "server" / "service.py"

    if not service_path.exists():
        raise RunnerError(
            f"service.py not found at {service_path}. "
            "Make sure you're in a restack-gen project directory."
        )

    return service_path


def load_env_file(base_dir: str | Path = ".") -> dict[str, str]:
    """Load environment variables from .env file if it exists.

    Args:
        base_dir: Base directory to search for .env

    Returns:
        Dictionary of environment variables loaded from .env
    """
    root = Path(base_dir).resolve()
    env_file = root / ".env"

    env_vars: dict[str, str] = {}
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()

    return env_vars


def start_service(
    config_path: str | None = None,
    base_dir: str | Path = ".",
    *,
    reload: bool = False,
) -> NoReturn:
    """Start the Restack service by executing server/service.py.

    Args:
        config_path: Optional path to config file (currently unused, reserved for future)
        base_dir: Base directory of the project
        reload: Enable auto-reload on file changes (not yet implemented)

    Raises:
        RunnerError: If service cannot be started
    """
    try:
        service_path = find_service_file(base_dir)
    except RunnerError as e:
        raise RunnerError(str(e)) from e

    # Load environment variables from .env if present
    env_vars = load_env_file(base_dir)
    env = {**os.environ, **env_vars}

    # If config_path provided, set it as environment variable for the service to use
    if config_path:
        env["RESTACK_CONFIG"] = config_path

    # Execute service.py as a subprocess for proper signal handling
    try:
        process = subprocess.Popen(
            [sys.executable, str(service_path)],
            env=env,
            cwd=str(Path(base_dir).resolve()),
        )

        # Set up signal handlers for graceful shutdown
        def handle_signal(signum: int, frame: object) -> None:
            """Handle interrupt signals and terminate subprocess gracefully."""
            print("\nShutting down service...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        # Wait for process to complete
        exit_code = process.wait()
        sys.exit(exit_code)

    except FileNotFoundError:
        raise RunnerError(f"Python executable not found: {sys.executable}") from None
    except Exception as e:
        raise RunnerError(f"Failed to start service: {e}") from e
```

---

## restack_gen\validator.py

<a id="restack_gen-validator-py"></a>

**File:** `restack_gen\validator.py`

```python
"""
Pipeline validation utilities.

This module provides validation for pipeline IR structures, including:
- Cycle detection in workflow graphs
- Unreachable node detection
- Resource existence validation
- Graph analysis utilities and summary stats

Public API:
- ValidationError: exception type
- validate_pipeline(root, strict=False) -> ValidationResult
"""

from dataclasses import dataclass
from typing import Any

from restack_gen.ir import Conditional, IRNode, Parallel, Resource, Sequence


class ValidationError(Exception):
    """Exception raised when pipeline validation fails."""

    pass


@dataclass
class ValidationResult:
    """Result of validating a pipeline IR.

    Attributes:
        is_valid: True if no errors were found
        errors: List of validation error messages
        warnings: List of non-fatal warnings
        stats: Dictionary of computed graph metrics (depth, resources, etc.)
    """

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    stats: dict[str, Any]


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
        """Validate the complete pipeline, raising on the first error."""
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
            raise ValidationError(f"Unreachable nodes detected: {', '.join(sorted(unreachable))}")

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


def validate_pipeline(root: IRNode, strict: bool = False) -> ValidationResult:
    """Validate a pipeline IR structure and return a rich result.

    The function aggregates errors and warnings instead of raising by default.
    In strict mode, warnings are treated as errors (but still returned, not raised).

    Args:
        root: Root node of the IR tree
        strict: When True, warnings will be promoted to errors in the result

    Returns:
        ValidationResult with validity, errors, warnings, and stats
    """
    validator = PipelineValidator(root)

    errors: list[str] = []
    warnings: list[str] = []

    # Collect structural errors
    try:
        validator._check_cycles()
    except ValidationError as e:
        errors.append(str(e))

    try:
        validator._check_unreachable_nodes()
    except ValidationError as e:
        errors.append(str(e))

    # Compute metrics and derive heuristic warnings
    stats = validator.get_graph_metrics()

    max_depth = stats.get("max_depth", 0)
    total_resources = stats.get("total_resources", 0)
    parallel_sections = stats.get("parallel_sections", 0)
    conditional_branches = stats.get("conditional_branches", 0)

    if max_depth > 5:
        warnings.append(
            f"Pipeline depth is high ({max_depth}); consider simplifying nested structures."
        )
    if total_resources > 20:
        warnings.append(
            f"Pipeline uses many resources ({total_resources}); consider splitting into sub-pipelines."
        )
    if parallel_sections > 10:
        warnings.append(
            f"Pipeline has many parallel sections ({parallel_sections}); monitor concurrency and resource usage."
        )
    if conditional_branches > 10:
        warnings.append(
            f"Pipeline has many conditional branches ({conditional_branches}); complexity may be high."
        )

    # Strict mode: promote warnings to errors in the returned result
    promoted_errors = list(errors)
    if strict and warnings:
        promoted_errors.extend([f"Strict mode: {w}" for w in warnings])

    is_valid = len(promoted_errors) == 0

    return ValidationResult(
        is_valid=is_valid,
        errors=promoted_errors,
        warnings=warnings,
        stats=stats,
    )
```

---

