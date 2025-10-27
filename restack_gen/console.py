"""Interactive console utilities for Restack projects.

Provides a lightweight wrapper around IPython so users can explore their
project with settings and paths preloaded.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType


class ConsoleError(Exception):
    """Raised when the interactive console cannot be started."""


def _load_module(module_path: Path) -> ModuleType:
    """Load a Python module from a file path.

    Args:
        module_path: The path to the module file (e.g., /path/to/mod.py)

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: If the path does not exist.
        ImportError: If the module could not be loaded.
    """
    module_path = Path(module_path)
    if not module_path.exists():
        raise FileNotFoundError(str(module_path))

    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec for module at {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    return module


def _discover_project_name(src_dir: Path) -> str | None:
    """Discover the project package name under src/.

    We expect exactly one package directory that contains common/settings.py.
    """
    for child in src_dir.iterdir():
        if child.is_dir() and (child / "common" / "settings.py").exists():
            return child.name
    return None


def start_console(config_path: str = "config/settings.yaml") -> None:
    """Start an interactive IPython session with project context.

    - Ensures IPython is available
    - Adds the project's src/ directory to sys.path
    - Loads settings from <project>.common.settings
    - Exposes `settings`, `project_name`, and `project_root` in user namespace

    Args:
        config_path: Path to project config to set in RESTACK_CONFIG env var

    Raises:
        ConsoleError: If prerequisites are missing (IPython missing, invalid project layout).
    """
    # Check IPython availability
    try:
        from IPython import embed  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised via tests
        raise ConsoleError("IPython is not installed. Install with 'pip install ipython'.") from exc

    project_root = Path.cwd()
    src_dir = project_root / "src"
    if not src_dir.exists():
        raise ConsoleError("No 'src/' directory found in the current project.")

    project_name = _discover_project_name(src_dir)
    if not project_name:
        raise ConsoleError("Could not determine project name/structure under src/.")

    # Add src/ to sys.path for module resolution
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Set environment variable for downstream code
    os.environ["RESTACK_CONFIG"] = config_path

    # Import settings module
    settings_module_name = f"{project_name}.common.settings"
    settings_mod = importlib.import_module(settings_module_name)
    settings_obj = getattr(settings_mod, "settings", {})

    # Prepare user namespace and launch IPython
    user_ns = {
        "settings": settings_obj,
        "project_name": project_name,
        "project_root": project_root,
    }

    # Start interactive console (tests patch embed to raise SystemExit)
    embed(user_ns=user_ns)
