"""ResearchWorkflow that uses a tool for web search and an LLM for summarization.

This workflow will:
- call a `web_search` tool (via FastMCP when configured, or a fake client)
- summarize the results with an LLM (real router if present, else a fake)
"""

from __future__ import annotations

from typing import Any

from research_agent.common.fallbacks import get_llm_router, get_tools_client
from restack_ai import Workflow, step


class ResearchWorkflow(Workflow):
    """End-to-end research demonstration using tools + LLM."""

    @step
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "restack agents")

        # 1) Use tools (FastMCP if configured) to search the web
        async with get_tools_client("research_tools") as client:
            search = await client.call_tool("web_search", {"query": query, "max_results": 3})

        # 2) Ask LLM to summarize results
        router = get_llm_router()
        messages = [
            {
                "role": "user",
                "content": f"Summarize the following results for: {query}\n"
                + str(search.get("results", [])),
            }
        ]
        llm_resp = await router.chat({"messages": messages})

        return {
            "query": query,
            "results": search.get("results", []),
            "summary": getattr(llm_resp, "content", ""),
            "metadata": getattr(llm_resp, "metadata", {}),
        }
