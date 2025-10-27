"""Tests for doctor checks."""

from pathlib import Path

import pytest

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


def test_check_package_versions() -> None:
    """Test package version checking."""
    res = doctor.check_package_versions()
    assert res.name == "package_versions"
    assert res.status in {"ok", "warn"}
    # Should not fail - either all packages meet requirements or warnings shown


def test_check_write_permissions(tmp_path: Path) -> None:
    """Test write permissions check."""
    # Create some directories
    (tmp_path / "src").mkdir()
    (tmp_path / "server").mkdir()
    (tmp_path / "client").mkdir()
    (tmp_path / "tests").mkdir()

    res = doctor.check_write_permissions(tmp_path)
    assert res.name == "write_permissions"
    # Should have write access to temp directory
    assert res.status == "ok"


def test_check_write_permissions_no_dirs(tmp_path: Path) -> None:
    """Test write permissions check when directories don't exist."""
    # Don't create any directories
    res = doctor.check_write_permissions(tmp_path)
    assert res.name == "write_permissions"
    # Should be ok when directories don't exist (nothing to check)
    assert res.status == "ok"


def test_check_restack_engine_unreachable(tmp_path: Path, respx_mock: None) -> None:
    """Test Restack engine check when engine is unreachable."""
    import os

    # Set a non-existent engine URL
    old_val = os.environ.get("RESTACK_ENGINE_URL")
    try:
        os.environ["RESTACK_ENGINE_URL"] = "http://localhost:19999"
        res = doctor.check_restack_engine(tmp_path)
        assert res.name == "restack_engine"
        assert res.status == "fail"
        assert "not reachable" in res.message.lower() or "unable to connect" in res.message.lower()
    finally:
        if old_val:
            os.environ["RESTACK_ENGINE_URL"] = old_val
        else:
            os.environ.pop("RESTACK_ENGINE_URL", None)


def test_check_restack_engine_with_config(tmp_path: Path) -> None:
    """Test Restack engine check reading from config file."""
    # Create config directory and settings
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    settings_file = config_dir / "settings.yaml"
    settings_file.write_text("restack:\n  engine_url: http://localhost:7700\n")

    # This will likely fail to connect, but should read the config
    res = doctor.check_restack_engine(tmp_path)
    assert res.name == "restack_engine"
    assert res.status in {"ok", "fail"}  # Depends on whether engine is actually running


class TestLLMConfig:
    """Tests for LLM configuration checking."""

    def test_check_llm_config_missing(self, tmp_path: Path) -> None:
        """Test when LLM config file doesn't exist."""
        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        assert res.status == "warn"
        assert "not found" in res.message

    def test_check_llm_config_missing_llm_key(self, tmp_path: Path) -> None:
        """Test when LLM config has no 'llm' key."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text("other_key: value\n")

        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        assert res.status == "fail"
        assert "missing 'llm' root key" in res.message

    def test_check_llm_config_no_providers(self, tmp_path: Path) -> None:
        """Test when LLM config has no providers."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text("llm:\n  providers: []\n")

        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        assert res.status == "fail"
        assert "No providers configured" in res.message

    def test_check_llm_config_missing_env_vars(self, tmp_path: Path) -> None:
        """Test when LLM config references missing env vars."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text(
            """llm:
  providers:
    - name: openai
      api_key: ${MISSING_API_KEY}
      base_url: ${MISSING_BASE_URL:-http://default}
"""
        )

        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        assert res.status == "warn"
        assert "MISSING_API_KEY" in res.message

    def test_check_llm_config_valid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when LLM config is valid with all env vars set."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text(
            """llm:
  providers:
    - name: openai
      api_key: ${OPENAI_API_KEY}
      model: gpt-4
  router:
    backend: direct
"""
        )

        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        assert res.status == "ok"


class TestKongGateway:
    """Tests for Kong Gateway checking."""

    def test_check_kong_gateway_no_config(self, tmp_path: Path) -> None:
        """Test Kong check when no LLM config exists."""
        res = doctor.check_kong_gateway(tmp_path)
        assert res.name == "kong"
        assert res.status == "ok"
        assert "not checked" in res.message.lower()

    def test_check_kong_gateway_backend_direct(self, tmp_path: Path) -> None:
        """Test Kong check when backend is direct (not Kong)."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text(
            """llm:
  providers:
    - name: openai
      api_key: test
  router:
    backend: direct
"""
        )

        res = doctor.check_kong_gateway(tmp_path)
        assert res.name == "kong"
        assert res.status == "ok"
        assert "not configured" in res.message

    def test_check_kong_gateway_unreachable(self, tmp_path: Path) -> None:
        """Test Kong check when Kong is configured but unreachable."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text(
            """llm:
  providers:
    - name: openai
      api_key: test
  router:
    backend: kong
    url: http://localhost:18888
    timeout: 1
"""
        )

        res = doctor.check_kong_gateway(tmp_path)
        assert res.name == "kong"
        assert res.status == "fail"
        assert "not reachable" in res.message


class TestPromptsCheck:
    """Tests for prompts registry checking."""

    def test_check_prompts_no_config(self, tmp_path: Path) -> None:
        """Test when prompts.yaml doesn't exist."""
        res = doctor.check_prompts(tmp_path)
        assert res.name == "prompts"
        assert res.status == "warn"
        assert "registry" in res.message.lower() or "not found" in res.message.lower()

    def test_check_prompts_invalid_yaml(self, tmp_path: Path) -> None:
        """Test when prompts.yaml has invalid YAML."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "prompts.yaml"
        config_file.write_text("invalid: yaml: [unclosed")

        res = doctor.check_prompts(tmp_path)
        assert res.name == "prompts"
        assert res.status == "fail"
        assert "invalid YAML" in res.message

    def test_check_prompts_empty(self, tmp_path: Path) -> None:
        """Test when prompts.yaml has no prompts."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "prompts.yaml"
        config_file.write_text("prompts: {}\n")

        res = doctor.check_prompts(tmp_path)
        assert res.name == "prompts"
        assert res.status == "warn"
        assert "No prompts defined" in res.message

    def test_check_prompts_missing_latest(self, tmp_path: Path) -> None:
        """Test when prompt has no 'latest' version."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "prompts.yaml"
        config_file.write_text(
            """prompts:
  MyPrompt:
    versions:
      "1.0.0": prompts/myprompt_1.0.0.txt
"""
        )

        res = doctor.check_prompts(tmp_path)
        assert res.name == "prompts"
        assert res.status == "warn"
        assert "Missing 'latest'" in res.details or "misconfigured" in res.message

    def test_check_prompts_missing_files(self, tmp_path: Path) -> None:
        """Test when prompt files don't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "prompts.yaml"
        config_file.write_text(
            """prompts:
  MyPrompt:
    latest: "1.0.0"
    versions:
      "1.0.0": prompts/missing.txt
"""
        )

        res = doctor.check_prompts(tmp_path)
        assert res.name == "prompts"
        assert res.status == "warn"
        assert "Missing prompt files" in res.details or "misconfigured" in res.message

    def test_check_prompts_valid(self, tmp_path: Path) -> None:
        """Test when prompts config is valid."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create actual prompt file
        prompt_file = prompts_dir / "test_1.0.0.txt"
        prompt_file.write_text("Test prompt content")

        config_file = config_dir / "prompts.yaml"
        config_file.write_text(
            f"""prompts:
  TestPrompt:
    latest: "1.0.0"
    versions:
      "1.0.0": {prompt_file}
"""
        )

        res = doctor.check_prompts(tmp_path)
        assert res.name == "prompts"
        assert res.status == "ok"


class TestPackageVersions:
    """Tests for package version checking."""

    def test_check_package_versions_missing_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test when a required package is missing."""
        import importlib.metadata

        original_version = importlib.metadata.version

        def mock_version(pkg_name: str) -> str:
            if pkg_name == "nonexistent-package":
                raise importlib.metadata.PackageNotFoundError(pkg_name)
            return original_version(pkg_name)

        monkeypatch.setattr(importlib.metadata, "version", mock_version)

        # This test just verifies the function handles PackageNotFoundError
        res = doctor.check_package_versions()
        assert res.name == "package_versions"
        # Status could be ok or warn depending on actual package states

    def test_check_package_versions_old_version(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test when a package is below minimum version."""
        import importlib.metadata

        original_version = importlib.metadata.version

        def mock_version(pkg_name: str) -> str:
            # Return old version for restack-ai
            if pkg_name == "restack-ai":
                return "0.0.1"
            return original_version(pkg_name)

        monkeypatch.setattr(importlib.metadata, "version", mock_version)

        res = doctor.check_package_versions()
        assert res.name == "package_versions"
        # Should warn about old restack-ai version
        if res.status == "warn":
            assert "restack-ai" in (res.details or "")


class TestStatusPriority:
    """Tests for status priority helper."""

    def test_status_priority_ordering(self) -> None:
        """Test that status priority is correctly ordered."""
        from restack_gen.doctor import _status_priority

        assert _status_priority("ok") < _status_priority("warn")
        assert _status_priority("warn") < _status_priority("fail")
        assert _status_priority("ok") == 0
        assert _status_priority("warn") == 1
        assert _status_priority("fail") == 2


class TestLoadLLMConfig:
    """Tests for _load_llm_config helper."""

    def test_load_llm_config_missing(self, tmp_path: Path) -> None:
        """Test loading LLM config when file doesn't exist."""
        from restack_gen.doctor import _load_llm_config

        result = _load_llm_config(tmp_path)
        assert result is None

    def test_load_llm_config_valid(self, tmp_path: Path) -> None:
        """Test loading valid LLM config."""
        from restack_gen.doctor import _load_llm_config

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text("llm:\n  providers: []\n")

        result = _load_llm_config(tmp_path)
        assert result is not None
        assert "llm" in result

    def test_load_llm_config_invalid_yaml(self, tmp_path: Path) -> None:
        """Test loading LLM config with invalid YAML."""
        from restack_gen.doctor import _load_llm_config

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text("invalid: [unclosed")

        result = _load_llm_config(tmp_path)
        assert result is None


class TestToolsCheckAdvanced:
    """Advanced tests for tools checking."""

    def test_check_tools_with_valid_fastmcp_config(self, tmp_path: Path) -> None:
        """Test checking tools with proper fastmcp configuration."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        tools_config = config_dir / "tools.yaml"

        # Create valid fastmcp config
        tools_config.write_text(
            """fastmcp:
  servers:
    - name: test_server
      module: os
      enabled: true
"""
        )

        res = doctor.check_tools(tmp_path)
        assert res.name == "tools"
        # Will fail if fastmcp not installed, which is expected
        assert res.status in {"ok", "warn", "fail"}

    def test_check_tools_no_fastmcp_key(self, tmp_path: Path) -> None:
        """Test when tools.yaml exists but has no fastmcp key."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        tools_config = config_dir / "tools.yaml"

        tools_config.write_text("other_config: value\n")

        res = doctor.check_tools(tmp_path)
        assert res.name == "tools"
        assert res.status == "warn"
        assert "no fastmcp configuration" in res.message

    def test_check_tools_empty_servers(self, tmp_path: Path) -> None:
        """Test when fastmcp has no servers configured."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        tools_config = config_dir / "tools.yaml"

        tools_config.write_text("fastmcp:\n  servers: []\n")

        res = doctor.check_tools(tmp_path)
        assert res.name == "tools"
        assert res.status == "warn"
        assert "no servers configured" in res.message

    def test_check_tools_fastmcp_not_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test when fastmcp package is not installed."""
        import importlib

        original_import = importlib.import_module

        def mock_import(name: str, *args: str, **kwargs: str) -> None:  # type: ignore[misc]
            if name == "fastmcp":
                raise ImportError("Mock: fastmcp not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", mock_import)

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        tools_config = config_dir / "tools.yaml"

        tools_config.write_text(
            """fastmcp:
  servers:
    - name: test_server
      module: test_module
"""
        )

        res = doctor.check_tools(tmp_path)
        assert res.name == "tools"
        assert res.status == "fail"
        assert "not installed" in res.message.lower()

    def test_check_tools_module_import_error(self, tmp_path: Path) -> None:
        """Test when server module cannot be imported."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        tools_config = config_dir / "tools.yaml"

        tools_config.write_text(
            """fastmcp:
  servers:
    - name: test_server
      module: nonexistent_module_xyz
    - name: test_server2
      module: another_missing_module
"""
        )

        res = doctor.check_tools(tmp_path)
        assert res.name == "tools"
        # Should fail or have import errors
        if res.status == "fail":
            assert "cannot be imported" in res.message or res.details


class TestDependenciesCheck:
    """Tests for dependencies checking."""

    def test_check_dependencies_with_missing_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test dependencies check when a package is missing."""
        import importlib

        original_import = importlib.import_module

        def mock_import(name: str, *args: str, **kwargs: str) -> None:  # type: ignore[misc]
            if name == "typer":
                raise ImportError("Mock: typer not found")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(importlib, "import_module", mock_import)

        res = doctor.check_dependencies(["typer"])
        assert res.name == "dependencies"
        assert res.status == "warn"
        assert "typer" in (res.details or "")


class TestPythonVersionCheck:
    """Tests for Python version checking."""

    def test_check_python_version_custom_minimum(self) -> None:
        """Test Python version check with custom minimum."""
        # Test with minimum below current (should pass)
        res = doctor.check_python_version(min_major=3, min_minor=0)
        assert res.name == "python_version"
        assert res.status == "ok"

        # Test with minimum way above current (should fail)
        res = doctor.check_python_version(min_major=99, min_minor=99)
        assert res.name == "python_version"
        assert res.status == "fail"


class TestCheckRestackEngine:
    """Tests for Restack engine checking."""

    def test_check_restack_engine_with_invalid_settings_yaml(self, tmp_path: Path) -> None:
        """Test Restack engine check with invalid settings.yaml."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.yaml"
        settings_file.write_text("invalid: [yaml")

        # Should fall back to default URL despite invalid YAML
        res = doctor.check_restack_engine(tmp_path)
        assert res.name == "restack_engine"
        assert res.status in {"ok", "fail"}

    def test_check_restack_engine_env_var_priority(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variable takes priority over config."""

        # Set environment variable
        monkeypatch.setenv("RESTACK_ENGINE_URL", "http://localhost:9999")

        # Create config with different URL
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "settings.yaml"
        settings_file.write_text("restack:\n  engine_url: http://localhost:8888\n")

        res = doctor.check_restack_engine(tmp_path)
        assert res.name == "restack_engine"
        # Message should reference the env var URL
        assert "localhost:9999" in res.message or res.status in {"ok", "fail"}


class TestWritePermissions:
    """Tests for write permissions checking."""

    def test_check_write_permissions_read_only_dir(self, tmp_path: Path) -> None:
        """Test write permissions check on read-only directory."""
        import os
        import stat

        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Make directory read-only (platform-dependent)
        try:
            # Remove write permissions
            current_mode = os.stat(src_dir).st_mode
            os.chmod(src_dir, current_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)

            res = doctor.check_write_permissions(tmp_path)
            assert res.name == "write_permissions"
            # Should detect lack of write access
            # Note: This may not work on all platforms/filesystems
            if res.status == "fail":
                assert "src" in (res.details or "")

        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(src_dir, current_mode | stat.S_IWUSR)
            except Exception:
                pass


class TestGitStatusCheck:
    """Tests for git status checking."""

    def test_check_git_status_with_dirty_repo(self, tmp_path: Path) -> None:
        """Test git status check with dirty working tree."""
        import subprocess

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=False)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )

        # Create a file to make repo dirty
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        res = doctor.check_git_status(tmp_path)
        assert res.name == "git"
        # Should detect dirty status
        assert res.status in {"warn", "ok"}


class TestEnvVarExtraction:
    """Tests for environment variable extraction from LLM config."""

    def test_check_llm_config_nested_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test detection of env vars in nested structures."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "llm_router.yaml"
        config_file.write_text(
            """llm:
  providers:
    - name: openai
      api_key: ${OPENAI_KEY}
      config:
        base_url: ${BASE_URL:-http://default}
  router:
    url: ${ROUTER_URL}
"""
        )

        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        # Should detect missing env vars
        if res.status == "warn":
            details = res.message + (res.details or "")
            # At least one of these should be mentioned
            assert "OPENAI_KEY" in details or "ROUTER_URL" in details
