"""Fallback clients used when real LLM/router or FastMCP tools are not configured.

These allow the example to run entirely offline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str
    metadata: dict[str, Any]


class FakeLLMRouter:
    async def chat(self, request: dict[str, Any]) -> LLMResponse:
        # Produce a tiny summary from provided snippets
        messages = request.get("messages", [])
        prompt = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        summary = (prompt[:120] + "...") if len(prompt) > 120 else prompt
        return LLMResponse(content=f"Summary: {summary}", metadata={"provider": "fake"})


class FakeFastMCPClient:
    def __init__(self, _server: str) -> None:
        self._server = _server

    async def call_tool(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        if name == "web_search":
            q = params.get("query", "")
            return {
                "results": [
                    {"title": f"Result about {q}", "url": "https://example.com/a"},
                    {"title": f"Another on {q}", "url": "https://example.com/b"},
                ]
            }
        return {"ok": True}

    async def aclose(self) -> None:  # for symmetry with real client
        return None


@asynccontextmanager
async def get_tools_client(name: str) -> AsyncIterator[FakeFastMCPClient]:
    """Yield real FastMCP client if available, else a fake one."""
    try:
        from research_agent.common.fastmcp_manager import FastMCPClient  # type: ignore

        async with FastMCPClient(name) as real:
            yield real
            return
    except Exception:
        client = FakeFastMCPClient(name)
        try:
            yield client
        finally:
            await client.aclose()


def get_llm_router():
    """Return real LLMRouter if available, else a fake one."""
    try:
        from research_agent.common.llm_router import LLMRouter  # type: ignore

        return LLMRouter()
    except Exception:
        return FakeLLMRouter()
