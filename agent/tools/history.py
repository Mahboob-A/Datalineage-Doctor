import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Incident, IncidentStatus

logger = structlog.get_logger(__name__)


async def find_past_incidents(
    table_fqn: str,
    limit: int = 5,
    db_session: AsyncSession | None = None,
) -> dict:
    """Return recent complete incidents for the same table FQN from local storage."""
    if db_session is None:
        return {"past_incidents": [], "count": 0}

    bounded_limit = max(1, min(limit, 20))
    try:
        result = await db_session.execute(
            select(Incident)
            .where(Incident.table_fqn == table_fqn)
            .where(Incident.status == IncidentStatus.COMPLETE)
            .order_by(Incident.triggered_at.desc())
            .limit(bounded_limit)
        )
    except Exception as exc:
        logger.warning(
            "find_past_incidents_query_failed", table_fqn=table_fqn, error=str(exc)
        )
        return {"error": str(exc), "tool": "find_past_incidents"}

    incidents = result.scalars().all()
    payload = [
        {
            "incident_id": str(incident.id),
            "triggered_at": incident.triggered_at.isoformat(),
            "root_cause_summary": incident.root_cause_summary or "",
            "confidence_label": incident.confidence_label.value,
        }
        for incident in incidents
    ]
    return {"past_incidents": payload, "count": len(payload)}
