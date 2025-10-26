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
) -> None:
    """
    Generate a new resource (agent, workflow, function, pipeline, tool-server, llm-config, or prompt).

    Examples:
        restack g agent Researcher
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
    results = doctor_mod.run_all_checks(base_dir=".", verbose=verbose, check_tools_flag=check_tools)

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
