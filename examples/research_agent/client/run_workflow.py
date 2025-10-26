"""
Client script to run the ResearchWorkflow.
"""

import asyncio

from restack_ai import Restack


async def main():
    client = Restack()

    workflow_id = f"research-{asyncio.get_event_loop().time()}"
    run_id = await client.schedule_workflow(
        workflow_name="ResearchWorkflow",
        workflow_id=workflow_id,
        input={"query": "latest AI news"},
    )

    print(f"Research workflow scheduled: {workflow_id}")
    result = await client.get_workflow_result(workflow_id=workflow_id, run_id=run_id)

    print("Summary:\n", result.get("summary"))


if __name__ == "__main__":
    asyncio.run(main())
