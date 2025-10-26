"""
Service module for prompted_pipeline.

Registers the PromptedPipelineWorkflow. This example includes a minimal
prompt loader that reads Markdown prompt files from the prompts/ directory.
"""

import asyncio

from restack_ai import Restack

from prompted_pipeline.workflows.prompted_pipeline_workflow import PromptedPipelineWorkflow


async def main():
    client = Restack()
    client.register_workflow(PromptedPipelineWorkflow)
    await client.start_service()


if __name__ == "__main__":
    asyncio.run(main())
