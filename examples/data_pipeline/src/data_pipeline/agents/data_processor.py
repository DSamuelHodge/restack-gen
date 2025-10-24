"""
DataProcessor agent implementation.

This agent processes and transforms fetched data.
"""

from typing import Any

from restack_ai import activity


@activity.defn
async def data_processor_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Process and transform data.

    Args:
        input_data: Input data from previous step (DataFetcher)

    Returns:
        Processed data with transformations applied
    """
    records = input_data.get("records", [])

    # Process records: filter and enrich
    processed_records = []
    total_value = 0

    for record in records:
        value = record.get("value", 0)
        # Filter: only keep records with value >= 150
        if value >= 150:
            processed_record = {
                **record,
                "processed": True,
                "value_category": "high" if value >= 200 else "medium",
            }
            processed_records.append(processed_record)
            total_value += value

    return {
        "status": "processed",
        "original_count": len(records),
        "processed_count": len(processed_records),
        "records": processed_records,
        "total_value": total_value,
        "average_value": total_value / len(processed_records) if processed_records else 0,
        "previous_step": input_data.get("status"),
    }
