"""
Service module for email_pipeline.

This module sets up and registers all agents and workflows.
"""

from restack_ai import Restack

from email_pipeline.agents.email_validator import email_validator_activity
from email_pipeline.agents.spam_checker import spam_checker_activity
from email_pipeline.agents.virus_scanner import virus_scanner_activity
from email_pipeline.agents.email_router import email_router_activity
from email_pipeline.agents.personal_handler import personal_handler_activity
from email_pipeline.agents.business_handler import business_handler_activity
from email_pipeline.workflows.email_pipeline_workflow import EmailPipelineWorkflow


async def main():
    """Initialize and run the Restack service."""
    client = Restack()

    # Register activities
    client.register_activity(email_validator_activity)
    client.register_activity(spam_checker_activity)
    client.register_activity(virus_scanner_activity)
    client.register_activity(email_router_activity)
    client.register_activity(personal_handler_activity)
    client.register_activity(business_handler_activity)

    # @generated-workflows-start
    client.register_workflow(EmailPipelineWorkflow)
    # @generated-workflows-end

    await client.start_service()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
