"""
VirusScanner agent implementation.

This agent scans emails for virus indicators.
"""

from typing import Any

from restack_ai import activity


@activity.defn
async def virus_scanner_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Scan email for virus indicators.

    Args:
        input_data: Input containing email data

    Returns:
        Virus scan result
    """
    email = input_data.get("email", {})
    attachments = email.get("attachments", [])

    # Simulate virus scanning
    suspicious_extensions = [".exe", ".bat", ".cmd", ".scr", ".vbs"]
    threats_found = []

    for attachment in attachments:
        filename = attachment.get("filename", "")
        if any(filename.endswith(ext) for ext in suspicious_extensions):
            threats_found.append(filename)

    is_safe = len(threats_found) == 0

    return {
        **input_data,
        "virus_scan": {
            "status": "scanned",
            "is_safe": is_safe,
            "threats_found": threats_found,
            "attachments_scanned": len(attachments),
        },
    }
