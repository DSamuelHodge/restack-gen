"""Tests for DataFetcher agent."""

import pytest
from data_pipeline.agents.data_fetcher import data_fetcher_activity


@pytest.mark.asyncio
async def test_data_fetcher_activity():
    """Test data fetcher returns expected data structure."""
    input_data = {"source": "test"}

    result = await data_fetcher_activity(input_data)

    assert result["status"] == "fetched"
    assert result["source"] == "external_api"
    assert "timestamp" in result
    assert "records" in result
    assert result["count"] == 3
    assert result["input"] == input_data


@pytest.mark.asyncio
async def test_data_fetcher_records():
    """Test fetched records have correct structure."""
    result = await data_fetcher_activity({})

    records = result["records"]
    assert len(records) == 3
    assert all("id" in r and "name" in r and "value" in r for r in records)
