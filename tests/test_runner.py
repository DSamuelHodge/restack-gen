"""Tests for the service runner module."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from restack_gen.runner import (
    RunnerError,
    find_service_file,
    load_env_file,
    start_service,
)


def test_find_service_file_success(tmp_path: Path) -> None:
    """Test finding service.py in standard project structure."""
    # Create server/service.py
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("# service code")

    result = find_service_file(tmp_path)
    assert result == service_file
    assert result.exists()


def test_find_service_file_missing(tmp_path: Path) -> None:
    """Test error when service.py is missing."""
    with pytest.raises(RunnerError, match="service.py not found"):
        find_service_file(tmp_path)


def test_load_env_file_exists(tmp_path: Path) -> None:
    """Test loading environment variables from .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
# Comment line
API_KEY=secret123
DATABASE_URL=postgres://localhost/db
EMPTY_LINE_BELOW=

FEATURE_FLAG=true
"""
    )

    env_vars = load_env_file(tmp_path)
    assert env_vars["API_KEY"] == "secret123"
    assert env_vars["DATABASE_URL"] == "postgres://localhost/db"
    assert env_vars["FEATURE_FLAG"] == "true"
    assert len(env_vars) == 4  # Three values plus EMPTY_LINE_BELOW


def test_load_env_file_missing(tmp_path: Path) -> None:
    """Test loading when .env file doesn't exist."""
    env_vars = load_env_file(tmp_path)
    assert env_vars == {}


def test_load_env_file_malformed(tmp_path: Path) -> None:
    """Test handling malformed .env entries."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
VALID_KEY=valid_value
NO_EQUALS_SIGN
# Comment
ANOTHER_VALID=123
"""
    )

    env_vars = load_env_file(tmp_path)
    assert "VALID_KEY" in env_vars
    assert "ANOTHER_VALID" in env_vars
    assert "NO_EQUALS_SIGN" not in env_vars


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_start_service_basic(mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path) -> None:
    """Test starting service with basic configuration."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    # Mock process that exits successfully
    mock_process = MagicMock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Execute - will sys.exit(0) on success
    with pytest.raises(SystemExit) as exc_info:
        start_service(base_dir=tmp_path)

    assert exc_info.value.code == 0
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == [sys.executable, str(service_file)]
    assert "env" in kwargs
    assert "cwd" in kwargs


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_start_service_with_config(
    mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path
) -> None:
    """Test starting service with config file path."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    mock_process = MagicMock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Execute with config
    with pytest.raises(SystemExit) as exc_info:
        start_service(config_path="config/prod.yaml", base_dir=tmp_path)

    assert exc_info.value.code == 0
    args, kwargs = mock_popen.call_args
    assert kwargs["env"]["RESTACK_CONFIG"] == "config/prod.yaml"


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_start_service_with_env_file(
    mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path
) -> None:
    """Test that .env variables are passed to subprocess."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    env_file = tmp_path / ".env"
    env_file.write_text("TEST_VAR=test_value\n")

    mock_process = MagicMock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Execute
    with pytest.raises(SystemExit) as exc_info:
        start_service(base_dir=tmp_path)

    assert exc_info.value.code == 0
    args, kwargs = mock_popen.call_args
    assert kwargs["env"]["TEST_VAR"] == "test_value"


def test_start_service_missing_service_file(tmp_path: Path) -> None:
    """Test error when service.py doesn't exist."""
    with pytest.raises(RunnerError, match="service.py not found"):
        start_service(base_dir=tmp_path)


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_start_service_nonzero_exit(
    mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path
) -> None:
    """Test handling of non-zero exit codes."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("import sys; sys.exit(1)")

    mock_process = MagicMock()
    mock_process.wait.return_value = 1
    mock_popen.return_value = mock_process

    # Execute - should propagate exit code
    with pytest.raises(SystemExit) as exc_info:
        start_service(base_dir=tmp_path)

    assert exc_info.value.code == 1


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_signal_handler_graceful_shutdown(
    mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path
) -> None:
    """Test that signal handlers are registered for graceful shutdown."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    mock_process = MagicMock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Execute
    with pytest.raises(SystemExit):
        start_service(base_dir=tmp_path)

    # Verify signal handlers were registered
    import signal

    signal_calls = mock_signal.call_args_list
    signal_types = [call[0][0] for call in signal_calls]
    assert signal.SIGINT in signal_types
    assert signal.SIGTERM in signal_types


@patch("restack_gen.runner.subprocess.Popen")
def test_signal_handler_invocation(mock_popen: MagicMock, tmp_path: Path) -> None:
    """Test that signal handler terminates the process correctly."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    mock_process = MagicMock()
    mock_process.wait.side_effect = [None, 0]  # First wait in handler, then main
    mock_popen.return_value = mock_process

    # Capture the signal handler
    captured_handler = None

    def capture_signal(signum: int, handler: object) -> None:
        nonlocal captured_handler
        if signum == 2:  # SIGINT
            captured_handler = handler

    with patch("restack_gen.runner.signal.signal", side_effect=capture_signal):
        with pytest.raises(SystemExit):
            start_service(base_dir=tmp_path)

        # Simulate SIGINT
        if captured_handler:
            with pytest.raises(SystemExit) as exc_info:
                captured_handler(2, None)  # type: ignore
            assert exc_info.value.code == 0
            mock_process.terminate.assert_called_once()


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_subprocess_exception(
    mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path
) -> None:
    """Test handling of subprocess exceptions."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    mock_popen.side_effect = FileNotFoundError("Python not found")

    # Execute
    with pytest.raises(RunnerError, match="Python executable not found"):
        start_service(base_dir=tmp_path)


@patch("restack_gen.runner.subprocess.Popen")
@patch("restack_gen.runner.signal.signal")
def test_subprocess_generic_exception(
    mock_signal: MagicMock, mock_popen: MagicMock, tmp_path: Path
) -> None:
    """Test handling of generic subprocess exceptions."""
    # Setup
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    service_file = server_dir / "service.py"
    service_file.write_text("print('service started')")

    mock_popen.side_effect = RuntimeError("Unknown error")

    # Execute
    with pytest.raises(RunnerError, match="Failed to start service"):
        start_service(base_dir=tmp_path)
