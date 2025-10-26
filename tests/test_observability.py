"""Targeted tests for observability helpers generated from templates.

These tests generate a temporary project, render the observability module,
import it dynamically, and verify the structured JSON logs emitted by the
async context managers for both success and error paths.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from types import ModuleType
from typing import Any

import pytest

from restack_gen.generator import generate_llm_config


def _import_module_from_path(module_name: str, file_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


class _ListHandler(logging.Handler):
    """Logging handler that collects messages in a list."""

    def __init__(self, sink: list[str]):
        super().__init__(level=logging.INFO)
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self._sink.append(record.getMessage())


def _attach_logger(module: ModuleType):
    """Attach a list-backed handler to the module's logger and return the sink + handler."""
    sink: list[str] = []
    handler = _ListHandler(sink)
    logger = logging.getLogger(module.__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return sink, handler, logger


def _detach_logger(logger: logging.Logger, handler: logging.Handler) -> None:
    try:
        logger.removeHandler(handler)
    except Exception:
        pass


def _ensure_json(line: str) -> dict[str, Any]:
    data = json.loads(line)
    assert isinstance(data, dict)
    return data


class TestObservabilityGeneration:
    def test_generate_llm_config_includes_observability(self, tmp_path, monkeypatch):
        project_root = tmp_path / "myproj"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text('name = "myproj"\n')

        monkeypatch.chdir(project_root)

        # Use generator; should return observability path
        files = generate_llm_config(force=True, backend="direct")
        assert "observability" in files
        assert files["observability"].exists()


@pytest.mark.asyncio
class TestObserveLLMCall:
    async def test_llm_call_success_logs(self, tmp_path, monkeypatch):
        project_root = tmp_path / "p1"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text('name = "p1"\n')
        monkeypatch.chdir(project_root)

        files = generate_llm_config(force=True)
        mod = _import_module_from_path(
            "gen_observability", str(files["observability"])  # type: ignore[index]
        )

        sink, handler, logger = _attach_logger(mod)
        try:
            # Run context and set usage
            correlation = {"run_id": "r-123", "agent_id": "a-xyz"}
            async with mod.observe_llm_call(  # type: ignore[attr-defined]
                correlation=correlation,
                provider="openai-primary",
                model="gpt-4o-mini",
                backend="direct",
            ) as ctx:
                ctx["usage"] = {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12}

            # Expect 2 log lines
            assert len(sink) == 2
            start = _ensure_json(sink[0])
            end = _ensure_json(sink[1])

            assert start["type"] == "llm_call_start"
            assert start["provider"] == "openai-primary"
            assert start["model"] == "gpt-4o-mini"
            assert start["backend"] == "direct"
            assert start.get("run_id") == "r-123"
            assert start.get("agent_id") == "a-xyz"

            assert end["type"] == "llm_call_end"
            assert end["status"] == "success"
            assert isinstance(end["duration_ms"], int)
            assert end["tokens"] == {"prompt": 5, "completion": 7, "total": 12}
        finally:
            _detach_logger(logger, handler)

    async def test_llm_call_error_logs(self, tmp_path, monkeypatch):
        project_root = tmp_path / "p2"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text('name = "p2"\n')
        monkeypatch.chdir(project_root)

        files = generate_llm_config(force=True)
        mod = _import_module_from_path("gen_obs2", str(files["observability"]))

        sink, handler, logger = _attach_logger(mod)
        try:
            correlation = {"run_id": "r-err", "agent_id": "a-err"}
            with pytest.raises(RuntimeError, match="boom"):
                async with mod.observe_llm_call(  # type: ignore[attr-defined]
                    correlation=correlation,
                    provider="openai-primary",
                    model="gpt-4o-mini",
                    backend="direct",
                ):
                    raise RuntimeError("boom")

            # Expect 2 log lines
            assert len(sink) == 2
            end = _ensure_json(sink[1])
            assert end["type"] == "llm_call_end"
            assert end["status"] == "error"
            assert end["error_type"] == "RuntimeError"
            assert end.get("run_id") == "r-err"
            assert end.get("agent_id") == "a-err"
        finally:
            _detach_logger(logger, handler)


@pytest.mark.asyncio
class TestObserveToolCall:
    async def test_tool_call_success_logs(self, tmp_path, monkeypatch):
        project_root = tmp_path / "p3"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text('name = "p3"\n')
        monkeypatch.chdir(project_root)

        files = generate_llm_config(force=True)
        mod = _import_module_from_path("gen_obs3", str(files["observability"]))

        sink, handler, logger = _attach_logger(mod)
        try:
            correlation = {"run_id": "r-tool", "agent_id": "a-tool"}
            async with mod.observe_tool_call(  # type: ignore[attr-defined]
                correlation=correlation, server="research_tools", tool="web_search"
            ):
                # simulate work
                pass

            assert len(sink) == 2
            start = _ensure_json(sink[0])
            end = _ensure_json(sink[1])
            assert start["type"] == "tool_call_start"
            assert start["server"] == "research_tools"
            assert start["tool"] == "web_search"
            assert end["type"] == "tool_call_end"
            assert end["status"] == "success"
            assert isinstance(end["duration_ms"], int)
        finally:
            _detach_logger(logger, handler)

    async def test_tool_call_error_logs(self, tmp_path, monkeypatch):
        project_root = tmp_path / "p4"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text('name = "p4"\n')
        monkeypatch.chdir(project_root)

        files = generate_llm_config(force=True)
        mod = _import_module_from_path("gen_obs4", str(files["observability"]))

        sink, handler, logger = _attach_logger(mod)
        try:
            with pytest.raises(ValueError, match="bad"):
                async with mod.observe_tool_call(  # type: ignore[attr-defined]
                    correlation={"run_id": "rr", "agent_id": "aa"},
                    server="research_tools",
                    tool="web_search",
                ):
                    raise ValueError("bad")

            assert len(sink) == 2
            end = _ensure_json(sink[1])
            assert end["type"] == "tool_call_end"
            assert end["status"] == "error"
            assert end["error_type"] == "ValueError"
        finally:
            _detach_logger(logger, handler)
