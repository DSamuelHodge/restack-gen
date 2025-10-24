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
