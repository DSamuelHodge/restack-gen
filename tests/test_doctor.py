"""Tests for doctor checks."""

from pathlib import Path

from restack_gen import doctor


def test_python_version_check() -> None:
    res = doctor.check_python_version()
    assert res.name == "python_version"
    assert res.status in {"ok", "fail"}
    # In CI and most dev, we should pass the minimum; don't assert exact version


def test_dependencies_check() -> None:
    res = doctor.check_dependencies()
    assert res.name == "dependencies"
    assert res.status in {"ok", "warn"}


def test_project_structure_library_repo(tmp_path: Path) -> None:
    # Simulate library repo presence
    pkg = tmp_path / "restack_gen"
    pkg.mkdir()
    res = doctor.check_project_structure(tmp_path)
    assert res.name == "project_structure"
    assert res.status == "ok"


def test_project_structure_generated_app(tmp_path: Path) -> None:
    # Simulate generated app presence
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname='demo'\n")
    (tmp_path / "server").mkdir()
    (tmp_path / "server" / "service.py").write_text("# svc")
    res = doctor.check_project_structure(tmp_path)
    assert res.status == "ok"


def test_project_structure_unknown(tmp_path: Path) -> None:
    res = doctor.check_project_structure(tmp_path)
    assert res.status == "warn"


def test_git_status_runs() -> None:
    # Should not raise, and returns a result
    res = doctor.check_git_status(".")
    assert res.name == "git"
    assert res.status in {"ok", "warn"}


def test_run_all_and_summarize(tmp_path: Path) -> None:
    # Run all checks against a temp dir (likely not a git repo)
    results = doctor.run_all_checks(tmp_path)
    assert results, "expected at least one check result"
    names = {r.name for r in results}
    assert {"python_version", "dependencies", "project_structure", "git"}.issubset(names)

    summary = doctor.summarize(results)
    assert set(summary.keys()) == {"ok", "warn", "fail", "overall"}
    assert summary["overall"] in {"ok", "warn", "fail"}
