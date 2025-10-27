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

from restack_gen.migration import MigrationError, MigrationRunner, MigrationStatus


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


def get_migration_status(target: str | None = None) -> list[MigrationStatus]:
    """Get status of all migrations.

    Args:
        target: Optional filter by target config (e.g., 'prompts')

    Returns:
        List of MigrationStatus objects

    Raises:
        RunnerError: If migration status check fails
    """
    from restack_gen.migration import MigrationRunner

    try:
        root = Path.cwd()
        runner = MigrationRunner(root)
        return runner.get_status(target=target)
    except Exception as e:
        raise RunnerError(f"Failed to get migration status: {e}") from e


def run_migrations_up(target: str | None = None, count: int | None = None) -> list[str]:
    """Apply pending migrations.

    Args:
        target: Optional filter by target config (e.g., 'prompts')
        count: Optional limit number of migrations to apply

    Returns:
        List of applied migration names

    Raises:
        RunnerError: If migration fails
    """
    from restack_gen.migration import MigrationError, MigrationRunner

    try:
        root = Path.cwd()
        runner = MigrationRunner(root)
        return runner.migrate_up(target=target, count=count)
    except MigrationError as e:
        raise RunnerError(f"Migration failed: {e}") from e


def run_migrations_down(target: str | None = None, count: int = 1) -> list[str]:
    """Rollback applied migrations.

    Args:
        target: Optional filter by target config (e.g., 'prompts')
        count: Number of migrations to rollback (default: 1)

    Returns:
        List of rolled back migration names

    Raises:
        RunnerError: If rollback fails
    """
    from restack_gen.migration import MigrationError, MigrationRunner

    try:
        root = Path.cwd()
        runner = MigrationRunner(root)
        return runner.migrate_down(target=target, count=count)
    except MigrationError as e:
        raise RunnerError(f"Rollback failed: {e}") from e
