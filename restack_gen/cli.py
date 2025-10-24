"""Main CLI application using Typer.

This module implements the Rails-style scaffolding commands for Restack.
"""

from typing import Annotated

import typer
from rich.console import Console

from restack_gen import __version__
from restack_gen.generator import (
    GenerationError,
    generate_agent,
    generate_function,
    generate_pipeline,
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
        str, typer.Argument(help="Type of resource: agent, workflow, function, or pipeline")
    ],
    name: Annotated[str, typer.Argument(help="Name of the resource to generate")],
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing files")] = False,
    operators: Annotated[
        str | None, typer.Option("--operators", "-o", help="Operator expression for pipeline (e.g., 'A → B ⇄ C')")
    ] = None,
) -> None:
    """
    Generate a new resource (agent, workflow, function, or pipeline).

    Examples:
        restack g agent Researcher
        restack g workflow EmailCampaign
        restack g function send_email
        restack g pipeline DataPipeline --operators "Fetch → Process ⇄ Store"
    """
    try:
        if resource_type == "agent":
            files = generate_agent(name, force=force)
            console.print(f"[green]✓[/green] Generated agent: [bold]{name}[/bold]")
            console.print(f"  Agent: {files['agent']}")
            console.print(f"  Test: {files['test']}")
            console.print(f"  Client: {files['client']}")
            console.print("\n[bold cyan]Next steps:[/bold cyan]")
            console.print("  1. Implement agent logic in the generated file")
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
                console.print("Example: restack g pipeline DataPipeline --operators \"Fetch → Process\"")
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

        else:
            console.print(f"[red]Error:[/red] Unknown resource type: {resource_type}")
            console.print("Valid types: agent, workflow, function")
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
    console.print(f"[yellow]Starting server with config:[/yellow] [bold]{config}[/bold]")
    console.print("[red]Not implemented yet - coming in PR 3[/red]")


@app.command()
def doctor(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show detailed output")] = False,
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

    Example:
        restack doctor
        restack doctor --verbose
    """
    console.print("[yellow]Running doctor checks...[/yellow]")
    console.print("[red]Not implemented yet - coming in PR 9[/red]")


if __name__ == "__main__":
    app()
