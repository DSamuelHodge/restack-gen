"""Prompted multi-step pipeline workflow.

This workflow loads a prompt and runs a simple multi-step process using the
operator grammar idea (sequential steps), while demonstrating prompt loading.
"""
from __future__ import annotations

from typing import Any

from prompted_pipeline.common.prompt_loader import load_prompt
from restack_ai import Workflow, step


class PromptedPipelineWorkflow(Workflow):
    """A minimal pipeline that uses a prompt to guide summarization."""

    @step
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        text = input_data.get("text", "")

        # Load prompt content
        prompt = load_prompt(base_dir=".", name="Analyze") or "Summarize the text:"

        # Step 1: Chunk (simulated)
        chunks = [text[i : i + 120] for i in range(0, len(text), 120)] or [text]

        # Step 2: Summarize each chunk (simulated)
        summaries = [f"{prompt}\n{c[:100]}..." if len(c) > 100 else f"{prompt}\n{c}" for c in chunks]

        # Step 3: Merge summaries (simulated)
        merged = "\n---\n".join(summaries)

        return {"chunks": len(chunks), "summary": merged}
