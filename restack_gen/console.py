"""Interactive shell for Restack application environment."""

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, NoReturn


class ConsoleError(Exception):
    """Raised when the console fails to start."""


def _load_module(path: Path) -> Any:
    """Dynamically load a module from a file path."""
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise ConsoleError(f"Failed to create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def start_console(config_path: str) -> NoReturn:
    """
    Load project environment and launch IPython console.

    Args:
        config_path: Path to settings configuration file.

    Raises:
        ConsoleError: If console startup fails
    """
    project_root = Path.cwd()

    try:
        # Check if IPython is available
        try:
            from IPython import embed  # type: ignore[import-not-found]
        except ImportError as e:
            raise ConsoleError(
                "IPython is not installed. Install it with: pip install ipython"
            ) from e

        # 1. Add project root to path for module discovery
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # 2. Set config environment variable
        os.environ["RESTACK_CONFIG"] = config_path

        # 3. Try to dynamically import the project's settings
        #    Assumes project_name is the first subdir in src/
        project_name = None
        src_path = project_root / "src"

        if not src_path.exists():
            raise ConsoleError("No 'src/' directory found. Are you in a restack-gen project?")

        for item in src_path.iterdir():
            if item.is_dir() and (item / "common" / "settings.py").exists():
                project_name = item.name
                break

        if not project_name:
            raise ConsoleError(
                "Could not determine project name/structure. "
                "Expected src/{project}/common/settings.py to exist."
            )

        settings_module_path = f"{project_name}.common.settings"
        settings_module = importlib.import_module(settings_module_path)
        settings = settings_module.settings  # settings instance loaded from settings.py

        # 4. Prepare local context for the console
        banner = f"Restack Console for '{project_name}'\n"
        banner += f"Settings loaded from: {config_path}\n"
        banner += "\nAvailable variables:\n"
        banner += "  - settings: Project settings object\n"
        banner += "  - project_name: Name of the project\n"
        banner += "  - project_root: Root directory path\n"

        local_vars = {
            "settings": settings,
            "project_name": project_name,
            "project_root": project_root,
        }

        # 5. Launch console
        print(banner)
        embed(user_ns=local_vars, colors="neutral")
        sys.exit(0)

    except ConsoleError:
        raise
    except Exception as e:
        raise ConsoleError(f"Failed to load environment: {e}") from e
