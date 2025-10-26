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
