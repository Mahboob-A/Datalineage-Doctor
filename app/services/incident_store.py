from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BlastRadiusConsumer, Incident, IncidentStatus, TimelineEvent


async def list_incidents(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> list[Incident]:
    offset = max(page - 1, 0) * page_size
    result = await db.execute(
        select(Incident)
        .order_by(desc(Incident.triggered_at))
        .offset(offset)
        .limit(page_size)
    )
    return list(result.scalars().all())


async def get_incident(db: AsyncSession, incident_id: str) -> Incident | None:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    return result.scalar_one_or_none()


async def get_incident_timeline(
    db: AsyncSession, incident_id: str
) -> list[TimelineEvent]:
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.incident_id == incident_id)
        .order_by(asc(TimelineEvent.sequence))
    )
    return list(result.scalars().all())


async def get_blast_radius(
    db: AsyncSession, incident_id: str
) -> list[BlastRadiusConsumer]:
    result = await db.execute(
        select(BlastRadiusConsumer)
        .where(BlastRadiusConsumer.incident_id == incident_id)
        .order_by(asc(BlastRadiusConsumer.level), asc(BlastRadiusConsumer.entity_fqn))
    )
    return list(result.scalars().all())


async def get_incident_detail(
    db: AsyncSession, incident_id: str
) -> tuple[Incident, list[TimelineEvent], list[BlastRadiusConsumer]] | None:
    incident = await get_incident(db, incident_id)
    if incident is None:
        return None
    timeline_events = await get_incident_timeline(db, incident_id)
    blast_radius = await get_blast_radius(db, incident_id)
    return incident, timeline_events, blast_radius


def group_blast_radius(
    blast_radius: list[BlastRadiusConsumer],
) -> dict[int, list[BlastRadiusConsumer]]:
    grouped: dict[int, list[BlastRadiusConsumer]] = {}
    for consumer in blast_radius:
        grouped.setdefault(consumer.level, []).append(consumer)
    return {level: grouped[level] for level in sorted(grouped)}


async def latest_incident(db: AsyncSession) -> Incident | None:
    result = await db.execute(
        select(Incident).order_by(desc(Incident.triggered_at)).limit(1)
    )
    return result.scalar_one_or_none()


def status_to_badge(status: IncidentStatus) -> str:
    return status.value.lower()
