"""
DataSaver agent implementation.

This agent saves processed data to a destination.
"""

from datetime import datetime
from typing import Any

from restack_ai import activity


@activity.defn
async def data_saver_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Save processed data to a destination.

    Args:
        input_data: Processed data from DataProcessor

    Returns:
        Confirmation of saved data
    """
    records = input_data.get("records", [])

    # Simulate saving to database or storage
    saved_ids = [record["id"] for record in records]

    return {
        "status": "saved",
        "destination": "database",
        "saved_count": len(records),
        "saved_ids": saved_ids,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_value": input_data.get("total_value", 0),
            "average_value": input_data.get("average_value", 0),
        },
        "pipeline_complete": True,
    }
