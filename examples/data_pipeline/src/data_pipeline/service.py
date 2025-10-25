"""
Service module for data_pipeline.

This module sets up and registers all agents and workflows.
"""

from restack_ai import Restack

from data_pipeline.agents.data_fetcher import data_fetcher_activity
from data_pipeline.agents.data_processor import data_processor_activity
from data_pipeline.agents.data_saver import data_saver_activity
from data_pipeline.workflows.data_pipeline_workflow import DataPipelineWorkflow


async def main():
    """Initialize and run the Restack service."""
    client = Restack()

    # Register activities
    client.register_activity(data_fetcher_activity)
    client.register_activity(data_processor_activity)
    client.register_activity(data_saver_activity)

    # @generated-workflows-start
    client.register_workflow(DataPipelineWorkflow)
    # @generated-workflows-end

    await client.start_service()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
