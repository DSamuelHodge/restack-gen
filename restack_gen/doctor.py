"""Environment and project health checks for `restack-gen`.

This module implements a set of checks used by the `restack doctor` command
to verify the local environment, dependencies, and basic project structure.

Design goals:
- Keep checks fast and side-effect free
- Return structured results that the CLI can render
- Be resilient: unexpected environments should degrade to warnings, not crash
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal
import importlib
import sys
import subprocess
import asyncio
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
            "tools",
            "ok",
            "No tool servers configured (config/tools.yaml not found)"
        )
    
    try:
        # Load tools configuration
        with open(tools_config) as f:
            data = yaml.safe_load(f)
        
        if not data or "fastmcp" not in data:
            return DoctorCheckResult(
                "tools",
                "warn",
                "tools.yaml exists but has no fastmcp configuration"
            )
        
        servers = data["fastmcp"].get("servers", [])
        if not servers:
            return DoctorCheckResult(
                "tools",
                "warn",
                "tools.yaml exists but has no servers configured"
            )
        
        # Check if fastmcp is installed
        try:
            importlib.import_module("fastmcp")
        except ImportError:
            return DoctorCheckResult(
                "tools",
                "fail",
                f"FastMCP not installed (found {len(servers)} configured servers)",
                details="Run: pip install fastmcp"
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
                details="\n".join(import_errors)
            )
        
        # Try to get health status from running servers (async check)
        try:
            health_results = asyncio.run(_check_tools_health_async(root))
            
            healthy = sum(1 for h in health_results.values() if h.get("status") == "healthy")
            running = sum(1 for h in health_results.values() if h.get("status") in ["healthy", "running"])
            stopped = sum(1 for h in health_results.values() if h.get("status") == "stopped")
            errors = sum(1 for h in health_results.values() if h.get("status") == "error")
            
            if errors > 0:
                status = "warn"
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
                details=f"Health check unavailable: {e}"
            )
    
    except yaml.YAMLError as e:
        return DoctorCheckResult(
            "tools",
            "fail",
            "tools.yaml contains invalid YAML",
            details=str(e)
        )
    except Exception as e:
        return DoctorCheckResult(
            "tools",
            "warn",
            "Unable to check tool servers",
            details=str(e)
        )


async def _check_tools_health_async(base_dir: Path) -> dict:
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
            manager_class = getattr(manager_module, "FastMCPServerManager")
            manager = manager_class()
            health_results = await manager.health_check_all()
            
            return health_results
        finally:
            os.chdir(original_cwd)
    
    except Exception:
        # Silently fail - health check is optional
        return {}


def run_all_checks(base_dir: str | Path = ".", *, verbose: bool = False, check_tools_flag: bool = False) -> list[DoctorCheckResult]:
    """Run all doctor checks and return individual results.
    
    Args:
        base_dir: Project root directory
        verbose: Include detailed information in results
        check_tools_flag: Whether to include tool server health checks
    
    Returns:
        List of check results
    """
    checks: list[DoctorCheckResult] = []

    checks.append(check_python_version())
    checks.append(check_dependencies())
    checks.append(check_project_structure(base_dir))
    checks.append(check_git_status(base_dir))
    
    if check_tools_flag:
        checks.append(check_tools(base_dir, verbose=verbose))

    return checks


def summarize(results: Iterable[DoctorCheckResult]) -> dict[str, int | Status]:
    """Summarize results and compute an overall status.

    Returns a dict with keys: ok, warn, fail, overall
    """
    counts = {"ok": 0, "warn": 0, "fail": 0}
    worst: Status = "ok"
    for r in results:
        counts[r.status] += 1
        if _status_priority(r.status) > _status_priority(worst):
            worst = r.status
    counts["overall"] = worst
    return counts
