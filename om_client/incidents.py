from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
import structlog

from app.config import settings
from om_client.client import OMClient, get_table_fqn_candidates
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


_INCIDENTS_API_SUPPORTED: bool | None = None
logger = structlog.get_logger(__name__)


def _swagger_url() -> str:
    """Build the OpenMetadata swagger URL from configured base URL."""
    parsed = urlsplit(settings.om_base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/api/v1"):
        path = path[: -len("/api/v1")]
    swagger_path = f"{path}/swagger.json" if path else "/swagger.json"
    return urlunsplit((parsed.scheme, parsed.netloc, swagger_path, "", ""))


async def _supports_incidents_api() -> bool:
    """Check if the running OpenMetadata version exposes incidents API."""
    global _INCIDENTS_API_SUPPORTED
    if _INCIDENTS_API_SUPPORTED is not None:
        return _INCIDENTS_API_SUPPORTED

    headers = {"Authorization": f"Bearer {settings.om_jwt_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_swagger_url(), headers=headers)
        response.raise_for_status()
        spec = response.json()

    paths = spec.get("paths", {})
    _INCIDENTS_API_SUPPORTED = any(
        path.endswith("/incidents") for path in paths.keys()
    )
    return _INCIDENTS_API_SUPPORTED


async def _resolve_table_fqn(om: OMClient, table_fqn: str) -> str | None:
    """Resolve the canonical OpenMetadata table FQN for incident creation."""
    for candidate in get_table_fqn_candidates(table_fqn):
        table = await om._get(f"/tables/name/{quote(candidate, safe='')}")
        if table.get("found", True):
            return candidate
    return None


async def create_incident(
    report: "RCAReport", table_fqn: str, incident_id: str
) -> str | None:
    """Create a new incident entity in OpenMetadata."""
    if not await _supports_incidents_api():
        logger.info(
            "om_incidents_api_not_supported",
            om_base_url=settings.om_base_url,
            table_fqn=table_fqn,
            incident_id=incident_id,
        )
        return None

    async with OMClient() as om:
        resolved_table_fqn = await _resolve_table_fqn(om, table_fqn)
        if resolved_table_fqn is None:
            return None

        payload = OMIncidentPayload(
            name=f"dld-{incident_id}",
            entityReference={"type": "table", "fqn": resolved_table_fqn},
            incidentType="dataQuality",
            description=report.root_cause_summary,
            severity=_severity_from_label(report.confidence_label.value),
        ).model_dump()
        response = await om._post("/incidents", payload=payload)

    if not response.get("found", True):
        return None

    value = response.get("id") or response.get("name")
    if value is None:
        return None
    return str(value)
