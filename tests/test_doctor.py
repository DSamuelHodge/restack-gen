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


def test_run_all_checks_with_verbose(tmp_path: Path) -> None:
    """Test running checks with verbose flag."""
    results = doctor.run_all_checks(tmp_path, verbose=True)
    assert len(results) >= 4
    # Verbose should still produce results
    for result in results:
        assert result.name
        assert result.status in {"ok", "warn", "fail"}


def test_run_all_checks_with_tools_flag(tmp_path: Path) -> None:
    """Test running checks with tool server checking."""
    results = doctor.run_all_checks(tmp_path, check_tools_flag=True)
    assert len(results) >= 5  # Should include tools check
    names = {r.name for r in results}
    assert "tools" in names


def test_check_tools_no_config(tmp_path: Path) -> None:
    """Test checking tools when no config exists."""
    res = doctor.check_tools(tmp_path)
    assert res.name == "tools"
    # May return "ok" if no config means no tools to check
    assert res.status in {"ok", "warn"}
    assert "not found" in res.message.lower() or "no tool" in res.message.lower()


def test_check_tools_with_config(tmp_path: Path) -> None:
    """Test checking tools with a valid config."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    tools_config = config_dir / "tools.yaml"

    # Create a minimal valid config
    tools_config.write_text(
        """
tools:
  - name: test_server
    module: test_module
    enabled: true
"""
    )

    res = doctor.check_tools(tmp_path)
    assert res.name == "tools"
    # Should fail because module doesn't exist, but config was parsed
    assert res.status in {"fail", "warn"}


def test_check_tools_invalid_yaml(tmp_path: Path) -> None:
    """Test checking tools with invalid YAML."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    tools_config = config_dir / "tools.yaml"

    # Invalid YAML
    tools_config.write_text("invalid: yaml: content: [unclosed")

    res = doctor.check_tools(tmp_path)
    assert res.name == "tools"
    assert res.status == "fail"
    assert "invalid YAML" in res.message


def test_check_tools_verbose(tmp_path: Path) -> None:
    """Test checking tools with verbose output."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    tools_config = config_dir / "tools.yaml"

    tools_config.write_text(
        """
tools:
  - name: test_server
    module: test_module
    enabled: true
"""
    )

    res = doctor.check_tools(tmp_path, verbose=True)
    assert res.name == "tools"
    # Verbose may include details
    assert res.status in {"fail", "warn", "ok"}


def test_summarize_all_ok() -> None:
    """Test summarizing when all checks pass."""
    results = [
        doctor.DoctorCheckResult("check1", "ok", "All good"),
        doctor.DoctorCheckResult("check2", "ok", "All good"),
    ]
    summary = doctor.summarize(results)
    assert summary["ok"] == 2
    assert summary["warn"] == 0
    assert summary["fail"] == 0
    assert summary["overall"] == "ok"


def test_summarize_with_warnings() -> None:
    """Test summarizing with warnings."""
    results = [
        doctor.DoctorCheckResult("check1", "ok", "All good"),
        doctor.DoctorCheckResult("check2", "warn", "Minor issue"),
    ]
    summary = doctor.summarize(results)
    assert summary["ok"] == 1
    assert summary["warn"] == 1
    assert summary["fail"] == 0
    assert summary["overall"] == "warn"


def test_summarize_with_failures() -> None:
    """Test summarizing with failures."""
    results = [
        doctor.DoctorCheckResult("check1", "ok", "All good"),
        doctor.DoctorCheckResult("check2", "warn", "Minor issue"),
        doctor.DoctorCheckResult("check3", "fail", "Critical error"),
    ]
    summary = doctor.summarize(results)
    assert summary["ok"] == 1
    assert summary["warn"] == 1
    assert summary["fail"] == 1
    assert summary["overall"] == "fail"


def test_doctor_check_result_creation() -> None:
    """Test creating DoctorCheckResult objects."""
    result = doctor.DoctorCheckResult(
        name="test_check", status="ok", message="Test message", details="Test details"
    )
    assert result.name == "test_check"
    assert result.status == "ok"
    assert result.message == "Test message"
    assert result.details == "Test details"


def test_check_git_status_not_a_repo(tmp_path: Path) -> None:
    """Test git status check on a non-git directory."""
    res = doctor.check_git_status(tmp_path)
    assert res.name == "git"
    # Should handle non-git directories gracefully
    assert res.status in {"ok", "warn"}


def test_project_structure_with_partial_structure(tmp_path: Path) -> None:
    """Test project structure with partial app structure."""
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname='test'\n")
    # Missing server directory
    res = doctor.check_project_structure(tmp_path)
    # Should detect pyproject but warn about incomplete structure
    assert res.status in {"ok", "warn"}
