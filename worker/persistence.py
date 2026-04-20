from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.schemas.report import RCAReport
from app.models import BlastRadiusConsumer, Incident, IncidentStatus, TimelineEvent


async def save_incident(
    db: AsyncSession,
    table_fqn: str,
    test_case_fqn: str,
    triggered_at: str,
    report: RCAReport | None = None,
    incident_id: UUID | None = None,
) -> UUID:
    if incident_id is None:
        incident = Incident(
            table_fqn=table_fqn,
            test_case_fqn=test_case_fqn,
            triggered_at=datetime.fromisoformat(triggered_at),
            status=IncidentStatus.PROCESSING,
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident.id

    query = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = query.scalar_one()
    if report is not None:
        incident.status = IncidentStatus.COMPLETE
        incident.completed_at = datetime.now(tz=UTC)
        incident.root_cause_summary = report.root_cause_summary
        incident.confidence_score = report.confidence_score
        incident.confidence_label = report.confidence_label
        incident.evidence_chain = report.evidence_chain
        incident.remediation_steps = report.remediation_steps
        incident.raw_report = report.model_dump(mode="json")
        incident.blast_radius_count = len(report.blast_radius_consumers)

        for event in report.timeline_events:
            db.add(
                TimelineEvent(
                    incident_id=incident.id,
                    occurred_at=event.occurred_at,
                    event_type=event.event_type,
                    entity_fqn=event.entity_fqn,
                    entity_type=event.entity_type,
                    description=event.description,
                    sequence=event.sequence,
                )
            )

        for consumer in report.blast_radius_consumers:
            db.add(
                BlastRadiusConsumer(
                    incident_id=incident.id,
                    entity_fqn=consumer.entity_fqn,
                    entity_type=consumer.entity_type,
                    level=consumer.level,
                    service=consumer.service,
                )
            )

    await db.commit()
    return incident.id
