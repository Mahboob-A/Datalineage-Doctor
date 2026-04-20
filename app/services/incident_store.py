from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Incident, IncidentStatus


async def list_incidents(db: AsyncSession, page: int = 1, page_size: int = 20) -> list[Incident]:
    offset = max(page - 1, 0) * page_size
    result = await db.execute(
        select(Incident).order_by(desc(Incident.triggered_at)).offset(offset).limit(page_size)
    )
    return list(result.scalars().all())


async def get_incident(db: AsyncSession, incident_id: str) -> Incident | None:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    return result.scalar_one_or_none()


async def latest_incident(db: AsyncSession) -> Incident | None:
    result = await db.execute(select(Incident).order_by(desc(Incident.triggered_at)).limit(1))
    return result.scalar_one_or_none()


def status_to_badge(status: IncidentStatus) -> str:
    return status.value.lower()
