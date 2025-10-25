"""
BusinessHandler agent implementation.

This agent handles business emails.
"""

from typing import Any

from restack_ai import activity


@activity.defn
async def business_handler_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Handle business emails.

    Args:
        input_data: Input containing email and routing decision

    Returns:
        Business handling result
    """
    email = input_data.get("email", {})
    sender = email.get("from", "")
    subject = email.get("subject", "")

    # Simulate business email handling
    actions = [
        "Moved to Business inbox",
        "Applied priority tags",
        "Added to task list",
        "Notified team members",
    ]

    return {
        **input_data,
        "handling": {
            "status": "handled",
            "handler": "BusinessHandler",
            "email_type": "business",
            "actions": actions,
            "folder": "Business",
            "priority": "high",
            "sender": sender,
            "subject": subject,
        },
    }
