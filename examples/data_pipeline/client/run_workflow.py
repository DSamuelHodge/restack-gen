"""
Client script to run the DataPipeline workflow.
"""

import asyncio

from restack_ai import Restack


async def main():
    """Execute the DataPipelineWorkflow."""
    client = Restack()

    workflow_id = f"data-pipeline-{asyncio.get_event_loop().time()}"
    run_id = await client.schedule_workflow(
        workflow_name="DataPipelineWorkflow",
        workflow_id=workflow_id,
        input={"source": "client", "request_id": workflow_id},
    )

    print(f"Workflow scheduled: {workflow_id}")
    print(f"Run ID: {run_id}")

    # Wait for result
    result = await client.get_workflow_result(
        workflow_id=workflow_id,
        run_id=run_id,
    )

    print("\nWorkflow completed!")
    print(f"Final result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
