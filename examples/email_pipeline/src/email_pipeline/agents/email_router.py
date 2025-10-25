"""
EmailRouter agent implementation.

This agent routes emails based on type (personal vs business).
"""

from typing import Any

from restack_ai import activity


@activity.defn
async def email_router_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Route email based on content and sender.

    Args:
        input_data: Input containing email and security check results

    Returns:
        Routing decision with email type
    """
    email = input_data.get("email", {})
    sender = email.get("from", "")
    subject = email.get("subject", "").lower()

    # Determine email type based on sender domain and subject
    business_domains = ["company.com", "corp.com", "enterprise.com"]
    is_business = any(domain in sender for domain in business_domains)

    business_keywords = ["invoice", "meeting", "report", "contract", "proposal"]
    has_business_keywords = any(keyword in subject for keyword in business_keywords)

    email_type = "business" if (is_business or has_business_keywords) else "personal"

    return {
        **input_data,
        "routing": {
            "status": "routed",
            "email_type": email_type,
            "is_business": is_business,
            "has_business_keywords": has_business_keywords,
        },
    }
