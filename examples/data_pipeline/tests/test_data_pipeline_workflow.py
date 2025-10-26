"""Tests for DataPipelineWorkflow."""

import pytest
from data_pipeline.workflows.data_pipeline_workflow import DataPipelineWorkflow


@pytest.mark.asyncio
async def test_data_pipeline_workflow_integration():
    """Test complete pipeline execution end-to-end."""
    workflow = DataPipelineWorkflow()

    input_data = {"source": "test", "request_id": "test-123"}

    # Execute the complete pipeline
    result = await workflow.execute(input_data)

    # Verify final result from DataSaver
    assert result["status"] == "saved"
    assert result["pipeline_complete"] is True
    assert result["saved_count"] == 2  # Bob and Charlie pass filter
    assert result["saved_ids"] == [2, 3]
    assert result["summary"]["total_value"] == 350
