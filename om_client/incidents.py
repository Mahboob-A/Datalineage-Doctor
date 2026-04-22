from __future__ import annotations

from typing import TYPE_CHECKING

from om_client.client import OMClient
from om_client.schemas.incident import OMIncidentPayload

if TYPE_CHECKING:
    from agent.schemas.report import RCAReport

SEVERITY_MAP = {
    "HIGH": "Severity2",
    "MEDIUM": "Severity3",
    "LOW": "Severity4",
}


def _severity_from_label(label: str) -> str:
    return SEVERITY_MAP.get(label.upper(), "Severity4")


async def create_incident(
    report: "RCAReport", table_fqn: str, incident_id: str
) -> str | None:
    """Create a new incident entity in OpenMetadata."""
    payload = OMIncidentPayload(
        name=f"dld-{incident_id}",
        entityReference={"type": "table", "fqn": table_fqn},
        incidentType="dataQuality",
        description=report.root_cause_summary,
        severity=_severity_from_label(report.confidence_label.value),
    ).model_dump()

    async with OMClient() as om:
        response = await om._post("/incidents", payload=payload)

    if not response.get("found", True):
        return None

    value = response.get("id") or response.get("name")
    if value is None:
        return None
    return str(value)
