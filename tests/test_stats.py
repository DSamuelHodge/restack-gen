"""Tests for stats command and reporting."""

from pathlib import Path

from rich.console import Console

from restack_gen.project import create_new_project
from restack_gen.stats import render_stats_report, run_stats_report


def _write(p: Path, content: str = "pass\n") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_run_stats_report_counts_and_categories(tmp_path, monkeypatch):
    # Create a minimal project
    project_dir = tmp_path / "myapp"
    create_new_project("myapp", parent_dir=tmp_path, force=False)
    monkeypatch.chdir(project_dir)

    # Add files across categories
    src_root = project_dir / "src" / "myapp"
    _write(src_root / "agents" / "alpha.py", "\n".join(["# a", "class A:", "    pass"]) + "\n")
    _write(src_root / "workflows" / "beta_workflow.py", "def beta():\n    return 1\n")
    _write(src_root / "functions" / "gamma.py", "def gamma():\n    return 2\n")
    _write(src_root / "tools" / "tool_x.py", "NAME='X'\n")
    _write(src_root / "common" / "utils.py", "def util():\n    ...\n")

    # Infra
    _write(project_dir / "tests" / "test_something.py", "def test_x():\n    assert True\n")
    _write(project_dir / "client" / "runner.py", "print('hi')\n")
    _write(project_dir / "config" / "settings.yaml", "version: 1.0.0\n")
    _write(project_dir / "server" / "extra.py", "# server side helper\n")

    report = run_stats_report(project_dir)

    # Basic totals
    totals = report["totals"]
    assert totals["files"] >= 9  # at least the ones we created
    assert totals["lines"] > 0
    assert totals["size_kb"] > 0

    # Category presence and counts (at least 1 per added)
    res = report["results"]
    assert res.get("agent", {}).get("total_files", 0) >= 1
    assert res.get("workflow", {}).get("total_files", 0) >= 1
    assert res.get("function", {}).get("total_files", 0) >= 1
    assert res.get("tool", {}).get("total_files", 0) >= 1
    assert res.get("common", {}).get("total_files", 0) >= 1

    # Infra categories
    assert res.get("test", {}).get("total_files", 0) >= 1
    assert res.get("client", {}).get("total_files", 0) >= 1
    assert res.get("config", {}).get("total_files", 0) >= 1
    assert res.get("server", {}).get("total_files", 0) >= 1

    # Project name resolved
    assert report["project_name"] == "myapp"


def test_render_stats_report_outputs(tmp_path, monkeypatch):
    # Create project and minimal file
    project_dir = tmp_path / "myapp"
    create_new_project("myapp", parent_dir=tmp_path, force=False)
    monkeypatch.chdir(project_dir)
    src_root = project_dir / "src" / "myapp"
    _write(src_root / "agents" / "alpha.py", "class A:\n    pass\n")

    report = run_stats_report(project_dir)

    # Capture console output
    console = Console(record=True)
    render_stats_report(report, console)
    output = console.export_text()

    assert "Project Statistics" in output
    assert "Resource Summary" in output
    assert "Project Totals" in output
