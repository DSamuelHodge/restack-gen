"""Code inspection and statistics reporting."""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table


class StatsError(Exception):
    """Raised when statistics reporting fails."""


def run_stats_report(base_dir: str | Path) -> Dict[str, Any]:
    """
    Scan project and generate code statistics.

    Args:
        base_dir: Root directory to scan

    Returns:
        Dictionary of statistics including results and totals

    Raises:
        StatsError: If project structure cannot be determined
    """
    root = Path(base_dir).resolve()

    results: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"total_files": 0, "total_lines": 0, "total_size_kb": 0.0}
    )
    file_map: Dict[str, List[Path]] = defaultdict(list)

    # Determine project name for src/{project_name} paths
    project_name = None
    src_path = root / "src"

    if src_path.exists():
        for item in src_path.iterdir():
            if item.is_dir() and (item / "common" / "settings.py").exists():
                project_name = item.name
                break

    if not project_name:
        raise StatsError(
            "Could not determine project name/structure. "
            "Expected src/{project}/common/settings.py to exist."
        )

    # 1. Scan files
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in [".py", ".yaml", ".md", ".toml", ".j2"]:
            try:
                size_kb = path.stat().st_size / 1024

                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)

                # Categorize the file
                category_key = "other"
                relative_path = path.relative_to(root)

                if relative_path.parts[0] == "tests":
                    category_key = "test"
                elif relative_path.parts[0] == "client":
                    category_key = "client"
                elif relative_path.parts[0] == "config":
                    category_key = "config"
                elif relative_path.parts[0] == "server":
                    category_key = "server"
                elif relative_path.parts[0] == "src" and len(relative_path.parts) > 2:
                    if relative_path.parts[1] == project_name and len(relative_path.parts) > 2:
                        if relative_path.parts[2] == "agents":
                            category_key = "agent"
                        elif relative_path.parts[2] == "workflows":
                            category_key = "workflow"
                        elif relative_path.parts[2] == "functions":
                            category_key = "function"
                        elif relative_path.parts[2] == "common":
                            category_key = "common"
                        elif relative_path.parts[2] == "tools":
                            category_key = "tool"
                elif relative_path.name in ["pyproject.toml", "Makefile", "README.md"]:
                    category_key = "root_config"
                elif "template" in str(relative_path):
                    category_key = "template"

                results[category_key]["total_files"] += 1
                results[category_key]["total_lines"] += lines
                results[category_key]["total_size_kb"] += size_kb
                file_map[category_key].append(path)

            except Exception:
                # Silently skip unreadable files or errors
                pass

    # 2. Post-processing and Totals
    total_files = sum(r["total_files"] for r in results.values())
    total_lines = sum(r["total_lines"] for r in results.values())
    total_size_kb = sum(r["total_size_kb"] for r in results.values())

    report = {
        "results": dict(results),
        "totals": {"files": total_files, "lines": total_lines, "size_kb": total_size_kb},
        "project_name": project_name,
    }

    return report


def render_stats_report(report: Dict[str, Any], console: Console) -> None:
    """
    Render the generated statistics report to the console.

    Args:
        report: Statistics report from run_stats_report()
        console: Rich console for rendering
    """
    console.rule(f"[bold cyan]Project Statistics: {report['project_name']}[/bold cyan]")

    # Table 1: Code and Resource Breakdown
    console.print("\n[bold underline]Code & Resource Breakdown:[/bold underline]\n")

    table = Table(title="Resource Summary", show_header=True, header_style="bold green")
    table.add_column("Category", style="cyan", justify="left")
    table.add_column("Files", justify="right")
    table.add_column("Lines", justify="right")
    table.add_column("Size (KB)", justify="right")
    table.add_column("Avg Lines/File", justify="right")

    # Resource categories to highlight
    resource_categories = ["agent", "workflow", "function", "tool", "common"]

    for category in resource_categories:
        data = report["results"].get(
            category, {"total_files": 0, "total_lines": 0, "total_size_kb": 0.0}
        )
        if data["total_files"] > 0:
            avg_lines = data["total_lines"] / data["total_files"]
            table.add_row(
                category.capitalize(),
                str(data["total_files"]),
                str(data["total_lines"]),
                f"{data['total_size_kb']:.1f}",
                f"{avg_lines:.1f}",
            )

    console.print(table)

    # Table 2: Infrastructure Files
    console.print("\n[bold underline]Infrastructure Files:[/bold underline]")
    infra_categories = ["test", "client", "server", "config", "template", "root_config"]

    for category in infra_categories:
        data = report["results"].get(
            category, {"total_files": 0, "total_lines": 0, "total_size_kb": 0.0}
        )
        if data["total_files"] > 0:
            console.print(
                f"  - {category.replace('_', ' ').title()}: "
                f"{data['total_files']} files, {data['total_lines']} lines, "
                f"{data['total_size_kb']:.1f} KB"
            )

    # Table 3: Project Totals
    console.print("\n[bold underline]Project Totals:[/bold underline]")
    console.print(f"  [bold]Total Files:[/bold] {report['totals']['files']}")
    console.print(f"  [bold]Total Lines of Code (LOC):[/bold] {report['totals']['lines']}")
    console.print(f"  [bold]Total Size:[/bold] {report['totals']['size_kb']:.1f} KB")

    console.rule("[dim]End of Report[/dim]")
