"""
Client script to run the PromptedPipelineWorkflow.
"""

import asyncio

from restack_ai import Restack


async def main():
    client = Restack()

    sample_text = (
        "Restack Gen helps you scaffold agents, workflows, and pipelines with good defaults. "
        "This example shows how a prompt can guide a simple multi-step pipeline."
    )

    workflow_id = f"prompted-pipeline-{asyncio.get_event_loop().time()}"
    run_id = await client.schedule_workflow(
        workflow_name="PromptedPipelineWorkflow",
        workflow_id=workflow_id,
        input={"text": sample_text},
    )

    print(f"Prompted pipeline workflow scheduled: {workflow_id}")
    result = await client.get_workflow_result(workflow_id=workflow_id, run_id=run_id)

    print("Summary:\n", result.get("summary"))


if __name__ == "__main__":
    asyncio.run(main())
