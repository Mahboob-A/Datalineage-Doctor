import asyncio
from time import perf_counter

from prometheus_client import start_http_server

from agent.loop import run_rca_agent
from agent.notifications import create_om_incident, notify_slack
from app.database import AsyncSessionLocal
from app.services.metrics import (
    blast_radius_size,
    rca_confidence_score,
    rca_duration_seconds,
    rca_errors_total,
    rca_requests_total,
)
from worker.celery_app import celery_app
from worker.persistence import save_incident, set_om_incident_id, set_slack_notified

try:
    # Expose worker-local Prometheus registry for app-side metrics aggregation.
    # Bind to 0.0.0.0 to ensure cross-container reachability.
    start_http_server(9101, addr="0.0.0.0")
except OSError:
    # Celery can import this module more than once; ignore duplicate binds.
    pass


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def rca_task(self, table_fqn: str, test_case_fqn: str, triggered_at: str) -> dict:
    started = perf_counter()
    try:
        result = asyncio.run(
            _run(
                table_fqn=table_fqn,
                test_case_fqn=test_case_fqn,
                triggered_at=triggered_at,
            )
        )
        rca_requests_total.labels(status="success").inc()
        return result
    except Exception:
        rca_requests_total.labels(status="failure").inc()
        rca_errors_total.labels(error_type="task_failure").inc()
        raise
    finally:
        rca_duration_seconds.observe(perf_counter() - started)


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
        rca_confidence_score.set(float(report.confidence_score))
        blast_radius_size.observe(float(len(report.blast_radius_consumers)))

        slack_success = await notify_slack(report, table_fqn, str(incident_id))
        if slack_success:
            await set_slack_notified(db, incident_id, True)

        om_incident_id = await create_om_incident(report, table_fqn, str(incident_id))
        if om_incident_id:
            await set_om_incident_id(db, incident_id, om_incident_id)
        return {"status": "complete", "incident_id": str(incident_id)}
