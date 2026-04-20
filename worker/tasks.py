import asyncio

from agent.loop import run_rca_agent
from app.database import AsyncSessionLocal
from worker.celery_app import celery_app
from worker.persistence import save_incident


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
        return {"status": "complete", "incident_id": str(incident_id)}
