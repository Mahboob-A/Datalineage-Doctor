from __future__ import annotations

from typing import Optional

import httpx
import structlog

from agent.schemas.report import RCAReport
from app.config import settings
from om_client.incidents import create_incident

logger = structlog.get_logger(__name__)

CONFIDENCE_EMOJI = {
    "HIGH": ":red_circle:",
    "MEDIUM": ":large_orange_circle:",
    "LOW": ":white_circle:",
}


def _truncate(value: str, limit: int = 200) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _incident_url(incident_id: str) -> str:
    base = settings.app_base_url.rstrip("/")
    return f"{base}/incidents/{incident_id}"


def _build_slack_payload(
    report: RCAReport,
    table_fqn: str,
    incident_id: str,
) -> dict[str, object]:
    confidence = report.confidence_label.value
    emoji = CONFIDENCE_EMOJI.get(confidence, ":white_circle:")
    summary = _truncate(report.root_cause_summary)
    blast_radius_count = len(report.blast_radius_consumers)

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} RCA Complete - {confidence} Confidence",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Table:*\n`{table_fqn}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*Blast Radius:*\n{blast_radius_count} downstream consumers"
                        ),
                    },
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Root Cause:*\n{summary}"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Incident"},
                        "url": _incident_url(incident_id),
                    }
                ],
            },
        ]
    }


async def notify_slack(report: RCAReport, table_fqn: str, incident_id: str) -> bool:
    """Send a Slack notification when RCA completes."""
    if not settings.slack_enabled or not settings.slack_webhook_url:
        return False

    payload = _build_slack_payload(report, table_fqn, incident_id)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.slack_webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("slack_notification_failed", error=str(exc))
        return False


async def create_om_incident(
    report: RCAReport, table_fqn: str, incident_id: str
) -> Optional[str]:
    """Create an OpenMetadata incident entry for the RCA report."""
    try:
        return await create_incident(report, table_fqn, incident_id)
    except Exception as exc:
        logger.warning("om_incident_creation_failed", error=str(exc))
        return None
