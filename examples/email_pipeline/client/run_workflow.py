"""
Client script to run the EmailPipeline workflow.
"""

import asyncio

from restack_ai import Restack


async def main():
    """Execute the EmailPipelineWorkflow with sample emails."""
    client = Restack()

    # Test with a personal email
    personal_email = {
        "email": {
            "from": "friend@gmail.com",
            "to": "user@example.com",
            "subject": "Let's catch up!",
            "body": "Hey, how have you been? Would love to meet up soon.",
            "attachments": [],
        }
    }

    workflow_id = f"email-pipeline-personal-{asyncio.get_event_loop().time()}"
    run_id = await client.schedule_workflow(
        workflow_name="EmailPipelineWorkflow",
        workflow_id=workflow_id,
        input=personal_email,
    )

    print(f"Personal email workflow scheduled: {workflow_id}")
    result = await client.get_workflow_result(workflow_id=workflow_id, run_id=run_id)
    print(f"Personal email result: {result.get('handling', {}).get('handler')}\n")

    # Test with a business email
    business_email = {
        "email": {
            "from": "ceo@company.com",
            "to": "user@example.com",
            "subject": "Q4 Report Review",
            "body": "Please review the attached Q4 financial report.",
            "attachments": [{"filename": "report.pdf", "size": 1024}],
        }
    }

    workflow_id = f"email-pipeline-business-{asyncio.get_event_loop().time()}"
    run_id = await client.schedule_workflow(
        workflow_name="EmailPipelineWorkflow",
        workflow_id=workflow_id,
        input=business_email,
    )

    print(f"Business email workflow scheduled: {workflow_id}")
    result = await client.get_workflow_result(workflow_id=workflow_id, run_id=run_id)
    print(f"Business email result: {result.get('handling', {}).get('handler')}\n")


if __name__ == "__main__":
    asyncio.run(main())
