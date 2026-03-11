"""Send alert notifications via webhook (Slack/Discord compatible)."""

import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def send_alert(
    webhook_url: str,
    endpoint_name: str,
    status: str,
    consecutive_failures: int,
    error_message: Optional[str] = None,
) -> bool:
    """Send an alert to a webhook URL.

    Compatible with Slack and Discord webhook formats.

    Returns:
        True if the alert was sent successfully.
    """
    if not webhook_url:
        logger.debug("No webhook URL configured, skipping alert")
        return False

    color = "#dc3545" if status == "DOWN" else "#ffc107"
    emoji = "🔴" if status == "DOWN" else "🟡"

    payload = {
        "text": f"{emoji} **{endpoint_name}** is {status}",
        "attachments": [
            {
                "color": color,
                "fields": [
                    {"title": "Endpoint", "value": endpoint_name, "short": True},
                    {"title": "Status", "value": status, "short": True},
                    {
                        "title": "Consecutive Failures",
                        "value": str(consecutive_failures),
                        "short": True,
                    },
                ],
            }
        ],
    }

    if error_message:
        payload["attachments"][0]["fields"].append(
            {"title": "Error", "value": error_message[:200], "short": False}
        )

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"Alert sent for {endpoint_name}")
        return True

    except requests.RequestException as exc:
        logger.error(f"Failed to send alert: {exc}")
        return False
