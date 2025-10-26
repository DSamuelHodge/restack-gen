"""
Service module for research_agent.

Registers the ResearchWorkflow. This example uses stub fallbacks by default
so it runs offline. If you generate LLM config and tool servers in your own
project, this example shows how to use them.
"""

import asyncio

from restack_ai import Restack

from research_agent.workflows.research_workflow import ResearchWorkflow


async def main():
    """Initialize and run the Restack service."""
    client = Restack()

    # Register workflows
    client.register_workflow(ResearchWorkflow)

    await client.start_service()


if __name__ == "__main__":
    asyncio.run(main())
