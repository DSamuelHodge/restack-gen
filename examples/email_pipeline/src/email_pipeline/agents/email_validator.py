"""
EmailValidator agent implementation.

This agent validates email structure and content.
"""

import re
from typing import Any

from restack_ai import activity


@activity.defn
async def email_validator_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate email structure and content.

    Args:
        input_data: Input containing email data

    Returns:
        Validation result with email details
    """
    email = input_data.get("email", {})
    sender = email.get("from", "")
    recipient = email.get("to", "")
    subject = email.get("subject", "")
    body = email.get("body", "")

    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    valid_sender = bool(re.match(email_pattern, sender))
    valid_recipient = bool(re.match(email_pattern, recipient))

    is_valid = valid_sender and valid_recipient and len(subject) > 0

    return {
        "status": "validated",
        "email": email,
        "valid": is_valid,
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "body_length": len(body),
        "validation_details": {
            "valid_sender": valid_sender,
            "valid_recipient": valid_recipient,
            "has_subject": len(subject) > 0,
        },
    }
