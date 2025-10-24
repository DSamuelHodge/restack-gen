"""
SpamChecker agent implementation.

This agent checks for spam indicators in emails.
"""

from typing import Any

from restack_ai import activity


@activity.defn
async def spam_checker_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Check email for spam indicators.

    Args:
        input_data: Input containing email data

    Returns:
        Spam check result
    """
    email = input_data.get("email", {})
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()

    # Spam keyword detection
    spam_keywords = ["winner", "free money", "click here", "limited time", "act now"]
    spam_score = sum(keyword in subject or keyword in body for keyword in spam_keywords)

    is_spam = spam_score >= 2

    return {
        **input_data,
        "spam_check": {
            "status": "checked",
            "is_spam": is_spam,
            "spam_score": spam_score,
            "keywords_found": [kw for kw in spam_keywords if kw in subject or kw in body],
        },
    }
