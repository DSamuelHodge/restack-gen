"""
PersonalHandler agent implementation.

This agent handles personal emails.
"""

from typing import Any

from restack_ai import activity


@activity.defn
async def personal_handler_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Handle personal emails.

    Args:
        input_data: Input containing email and routing decision

    Returns:
        Personal handling result
    """
    email = input_data.get("email", {})
    sender = email.get("from", "")
    subject = email.get("subject", "")

    # Simulate personal email handling
    actions = [
        "Moved to Personal inbox",
        "Applied personal filters",
        "Updated contact info",
    ]

    return {
        **input_data,
        "handling": {
            "status": "handled",
            "handler": "PersonalHandler",
            "email_type": "personal",
            "actions": actions,
            "folder": "Personal",
            "sender": sender,
            "subject": subject,
        },
    }
