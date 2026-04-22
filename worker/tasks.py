import asyncio

from agent.loop import run_rca_agent
from agent.notifications import create_om_incident, notify_slack
from app.database import AsyncSessionLocal
from worker.celery_app import celery_app
from worker.persistence import save_incident, set_om_incident_id, set_slack_notified


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def rca_task(self, table_fqn: str, test_case_fqn: str, triggered_at: str) -> dict:
    return asyncio.run(
        _run(
            table_fqn=table_fqn, test_case_fqn=test_case_fqn, triggered_at=triggered_at
        )
    )


async def _run(table_fqn: str, test_case_fqn: str, triggered_at: str) -> dict:
    async with AsyncSessionLocal() as db:
        incident_id = await save_incident(
            db,
            table_fqn=table_fqn,
            test_case_fqn=test_case_fqn,
            triggered_at=triggered_at,
        )
        report = await run_rca_agent(
            table_fqn=table_fqn,
            test_case_fqn=test_case_fqn,
            triggered_at=triggered_at,
            db_session=db,
            incident_id=incident_id,
        )
        await save_incident(
            db,
            table_fqn=table_fqn,
            test_case_fqn=test_case_fqn,
            triggered_at=triggered_at,
            report=report,
            incident_id=incident_id,
        )

        slack_success = await notify_slack(report, table_fqn, str(incident_id))
        if slack_success:
            await set_slack_notified(db, incident_id, True)

        om_incident_id = await create_om_incident(report, table_fqn, str(incident_id))
        if om_incident_id:
            await set_om_incident_id(db, incident_id, om_incident_id)
        return {"status": "complete", "incident_id": str(incident_id)}
