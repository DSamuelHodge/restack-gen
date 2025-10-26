"""Tests for DataProcessor agent."""

import pytest
from data_pipeline.agents.data_processor import data_processor_activity


@pytest.mark.asyncio
async def test_data_processor_activity():
    """Test data processor filters and enriches data."""
    input_data = {
        "status": "fetched",
        "records": [
            {"id": 1, "name": "Alice", "value": 100},
            {"id": 2, "name": "Bob", "value": 200},
            {"id": 3, "name": "Charlie", "value": 150},
        ],
    }

    result = await data_processor_activity(input_data)

    assert result["status"] == "processed"
    assert result["original_count"] == 3
    assert result["processed_count"] == 2  # Only Bob and Charlie (value >= 150)
    assert result["previous_step"] == "fetched"


@pytest.mark.asyncio
async def test_data_processor_filtering():
    """Test processor filters low-value records."""
    input_data = {
        "records": [
            {"id": 1, "value": 50},
            {"id": 2, "value": 250},
        ],
    }

    result = await data_processor_activity(input_data)

    assert len(result["records"]) == 1
    assert result["records"][0]["id"] == 2


@pytest.mark.asyncio
async def test_data_processor_enrichment():
    """Test processor adds value categories."""
    input_data = {
        "records": [
            {"id": 1, "value": 180},
            {"id": 2, "value": 250},
        ],
    }

    result = await data_processor_activity(input_data)

    records = result["records"]
    assert records[0]["value_category"] == "medium"
    assert records[1]["value_category"] == "high"
    assert all(r["processed"] is True for r in records)
