"""
DataFetcher agent implementation.

This agent simulates fetching data from an external source.
"""

from datetime import datetime
from typing import Any

from restack_ai import activity


@activity.defn
async def data_fetcher_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch data from an external source.

    Args:
        input_data: Input data containing fetch parameters

    Returns:
        Fetched data with metadata
    """
    # Simulate fetching data from an API or database
    fetched_records = [
        {"id": 1, "name": "Alice", "value": 100},
        {"id": 2, "name": "Bob", "value": 200},
        {"id": 3, "name": "Charlie", "value": 150},
    ]

    return {
        "status": "fetched",
        "source": "external_api",
        "timestamp": datetime.now().isoformat(),
        "records": fetched_records,
        "count": len(fetched_records),
        "input": input_data,
    }
