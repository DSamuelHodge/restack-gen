"""Regression test: the generated LLM router module should import and
instantiate LLMRequest without Pydantic forward ref errors when the module
is loaded via importlib (mirroring integration tests).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from restack_gen.generator import generate_llm_config


def _import_router_from_file(py_file: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("generated_llm_router", str(py_file))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


@pytest.mark.asyncio
async def test_import_and_instantiation(tmp_path, monkeypatch) -> None:
    # Arrange: minimal project root
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    # Write a minimal pyproject marker so project discovery works
    (project_root / "pyproject.toml").write_text('name = "myproject"\n')
    monkeypatch.chdir(project_root)

    # Generate router/config files
    files = generate_llm_config(force=True, backend="direct")

    # Dynamically import the generated router module
    router_mod = _import_router_from_file(files["router"])  # type: ignore[index]

    # Access classes and instantiate LLMRequest
    LLMRequest = router_mod.LLMRequest
    # Should not raise PydanticUserError for postponed annotations
    req = LLMRequest(messages=[{"role": "user", "content": "hi"}], dry_run=True)

    # Basic assertions on instance
    assert req.messages[0]["content"] == "hi"
    assert req.dry_run is True
