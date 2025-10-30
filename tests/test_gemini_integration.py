"""Integration tests to ensure generated LLM router works with Gemini provider.

These tests generate a temporary project, write a config that uses a Gemini
provider (and optional OpenAI fallback), dynamically import the generated
router module, and mock HTTP calls using respx.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import respx
from httpx import Response

from restack_gen.generator import generate_llm_config


def _import_router_from_file(py_file: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("generated_llm_router", str(py_file))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


@pytest.mark.asyncio
async def test_gemini_direct_success_parsing(tmp_path, monkeypatch) -> None:
    """Router parses a valid Gemini response via direct REST path."""
    # Arrange: temp project
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text('name = "myproject"\n')
    monkeypatch.chdir(project_root)

    # Generate default files
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GEMINI_API_KEY", "KEY")
        files = generate_llm_config(force=True, backend="direct")

    # Overwrite config with Gemini-only provider
    cfg_path = files["config"]
    cfg_path.write_text(
        """
llm:
  router:
    backend: "direct"
    timeout: 10
  providers:
    - name: "gemini-test"
      type: "gemini"
      model: "gemini-2.5-flash"
      base_url: "http://mock-gemini"
      api_key: "${GEMINI_API_KEY}"
      priority: 1
  fallback:
    conditions: ["timeout", "5xx", "rate_limit", "malformed_response", "llm_error"]
    max_retries_per_provider: 1
    circuit_breaker:
      enabled: false
"""
    )

    # Dynamic import router module
    router_mod = _import_router_from_file(files["router"])  # type: ignore[index]
    LLMRouter = router_mod.LLMRouter
    LLMRequest = router_mod.LLMRequest

    # Mock Gemini REST endpoint
    with respx.mock(assert_all_called=True) as rsx:
        rsx.post(
            "http://mock-gemini/v1beta/models/gemini-2.5-flash:generateContent",
            params={"key": "KEY"},
        ).mock(
            return_value=Response(
                200,
                json={
                    "model": "gemini-2.5-flash",
                    "candidates": [
                        {
                            "content": {"parts": [{"text": "Hello from Gemini"}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 3,
                        "candidatesTokenCount": 4,
                        "totalTokenCount": 7,
                    },
                },
            )
        )

        async with LLMRouter(str(cfg_path)) as router:
            req = LLMRequest(
                messages=[{"role": "user", "content": "Say hi."}],
                temperature=0.0,
                max_tokens=32,
            )
            resp = await router.chat(req)

    # Assert
    assert resp.content == "Hello from Gemini"
    assert resp.model == "gemini-2.5-flash"
    assert resp.provider == "gemini-test"
    assert resp.finish_reason in {"STOP", "stop"}
    assert resp.usage == {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}


@pytest.mark.asyncio
async def test_gemini_200_error_body_fallback_to_openai(tmp_path, monkeypatch) -> None:
    """Gemini returns 200 with error body -> router falls back to OpenAI provider."""
    # Arrange: temp project
    project_root = tmp_path / "myproject"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text('name = "myproject"\n')
    monkeypatch.chdir(project_root)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GEMINI_API_KEY", "KEY")
        mp.setenv("OPENAI_API_KEY", "OPENAI_KEY")
        files = generate_llm_config(force=True, backend="direct")

    # Overwrite config with Gemini then OpenAI
    cfg_path = files["config"]
    cfg_path.write_text(
        """
llm:
  router:
    backend: "direct"
    timeout: 10
  providers:
    - name: "gemini-primary"
      type: "gemini"
      model: "gemini-2.5-flash"
      base_url: "http://mock-gemini"
      api_key: "${GEMINI_API_KEY}"
      priority: 1
    - name: "openai-fallback"
      type: "openai"
      model: "gpt-4o-mini"
      base_url: "http://mock-openai/v1"
      api_key: "${OPENAI_API_KEY}"
      priority: 2
  fallback:
    conditions: ["timeout", "5xx", "rate_limit", "malformed_response", "llm_error"]
    max_retries_per_provider: 1
    circuit_breaker:
      enabled: false
"""
    )

    # Import router
    router_mod = _import_router_from_file(files["router"])  # type: ignore[index]
    LLMRouter = router_mod.LLMRouter
    LLMRequest = router_mod.LLMRequest

    # Mock endpoints
    with respx.mock(assert_all_called=True) as rsx:
        # Gemini returns 200 with error body
        rsx.post(
            "http://mock-gemini/v1beta/models/gemini-2.5-flash:generateContent",
            params={"key": "KEY"},
        ).mock(return_value=Response(200, json={"error": {"message": "bad request"}}))

        # OpenAI fallback returns a valid response
        rsx.post("http://mock-openai/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "model": "gpt-4o-mini",
                    "choices": [
                        {"message": {"content": "Hello from OpenAI"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
                },
            )
        )

        async with LLMRouter(str(cfg_path)) as router:
            req = LLMRequest(
                messages=[{"role": "user", "content": "Say hi."}],
                temperature=0.0,
                max_tokens=32,
            )
            resp = await router.chat(req)

    # Assert fallback happened and OpenAI response is returned
    assert resp.content == "Hello from OpenAI"
    assert resp.provider == "openai-fallback"
    assert resp.model == "gpt-4o-mini"
    assert resp.finish_reason in {"stop", "length", "content_filter", "tool_calls", "tool_call"}
    assert resp.usage == {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}
