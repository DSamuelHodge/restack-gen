"""Tests for DataSaver agent."""

import pytest
from data_pipeline.agents.data_saver import data_saver_activity


@pytest.mark.asyncio
async def test_data_saver_activity():
    """Test data saver saves records and returns summary."""
    input_data = {
        "records": [
            {"id": 2, "name": "Bob", "value": 200},
            {"id": 3, "name": "Charlie", "value": 150},
        ],
        "total_value": 350,
        "average_value": 175,
    }

    result = await data_saver_activity(input_data)

    assert result["status"] == "saved"
    assert result["destination"] == "database"
    assert result["saved_count"] == 2
    assert result["saved_ids"] == [2, 3]
    assert result["pipeline_complete"] is True
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_data_saver_summary():
    """Test saver includes summary statistics."""
    input_data = {
        "records": [{"id": 1, "value": 100}],
        "total_value": 100,
        "average_value": 100,
    }

    result = await data_saver_activity(input_data)

    summary = result["summary"]
    assert summary["total_value"] == 100
    assert summary["average_value"] == 100
