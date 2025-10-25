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


def run_all_checks(base_dir: str | Path = ".", *, verbose: bool = False) -> list[DoctorCheckResult]:
    """Run all doctor checks and return individual results."""
    checks: list[DoctorCheckResult] = []

    checks.append(check_python_version())
    checks.append(check_dependencies())
    checks.append(check_project_structure(base_dir))
    checks.append(check_git_status(base_dir))

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
