# Worker Service Implementation Guide

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## What This Service Owns

The `worker/` directory owns all Celery task management. It is the boundary between the message queue and the agent module. It owns: the Celery application instance, task definitions, task retry configuration, the database write that persists the `RCAReport` returned by the agent, and task lifecycle metrics. It does not own reasoning logic (that is `agent/`) or HTTP routes (that is `app/`).

**Relationship to `agent/`:** The worker is the **caller**; the agent is the **reasoner**. The worker task calls `run_rca_agent()`, receives an `RCAReport`, and writes it to PostgreSQL. All reasoning, tool calls, and LLM interactions happen inside `agent/` and are invisible to the worker except as an awaited return value.

---

## Directory Structure

```
worker/
├── __init__.py
├── celery_app.py          # Celery application instance and configuration
├── tasks.py               # rca_task() definition — the only task in MVP
└── persistence.py         # DB write logic: save RCAReport → incident rows
```

---

## Key Patterns

### Celery App — `celery_app.py`

The Celery app instance is created here and imported by both `tasks.py` and the FastAPI app (for `.delay()` calls).

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "datalineage_doctor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,          # Task results kept in Redis for 1 hour
    worker_prefetch_multiplier=1, # One task at a time per worker process
)
```

### Task Definition — `tasks.py`

`rca_task` is the single Celery task for MVP. It orchestrates the full RCA lifecycle.

```python
import asyncio
from worker.celery_app import celery_app
from agent.loop import run_rca_agent
from worker.persistence import save_incident
from app.database import AsyncSessionLocal

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,       # seconds before first retry
    autoretry_for=(Exception,),
    retry_backoff=True,           # exponential: 30s, 60s, 120s
    retry_backoff_max=120,
    name="worker.tasks.rca_task",
)
def rca_task(self, table_fqn: str, test_case_fqn: str, triggered_at: str) -> dict:
    return asyncio.run(_run(self, table_fqn, test_case_fqn, triggered_at))


async def _run(task, table_fqn: str, test_case_fqn: str, triggered_at: str) -> dict:
    async with AsyncSessionLocal() as db:
        # Create a PROCESSING incident row immediately so the dashboard shows it
        incident_id = await save_incident(db, table_fqn, test_case_fqn, triggered_at)

        report = await run_rca_agent(
            table_fqn=table_fqn,
            test_case_fqn=test_case_fqn,
            triggered_at=triggered_at,
            db_session=db,
        )

        await save_incident(db, table_fqn, test_case_fqn, triggered_at,
                            report=report, incident_id=incident_id)

    return {"incident_id": str(incident_id), "status": "complete"}
```

Why `asyncio.run()` inside a sync Celery task: Celery workers run in sync processes. The `agent/` and `om_client/` modules are fully async. `asyncio.run()` bridges them. One event loop per task execution; no shared state between tasks.

### Persistence — `persistence.py`

Writes the `RCAReport` from the agent into the PostgreSQL tables. Separating this from `tasks.py` keeps the task definition readable and the DB logic independently testable.

```python
async def save_incident(
    db: AsyncSession,
    table_fqn: str,
    test_case_fqn: str,
    triggered_at: str,
    report: RCAReport | None = None,
    incident_id: uuid.UUID | None = None,
) -> uuid.UUID:
    if incident_id is None:
        # Initial creation — PROCESSING status
        incident = Incident(
            table_fqn=table_fqn,
            test_case_fqn=test_case_fqn,
            triggered_at=datetime.fromisoformat(triggered_at),
            status=IncidentStatus.PROCESSING,
        )
        db.add(incident)
        await db.flush()
        return incident.id

    # Update with completed report
    incident = await db.get(Incident, incident_id)
    incident.status = IncidentStatus.COMPLETE
    incident.completed_at = datetime.now(UTC)
    incident.root_cause_summary = report.root_cause_summary
    incident.confidence_score = report.confidence_score
    incident.confidence_label = report.confidence_label
    incident.evidence_chain = report.evidence_chain
    incident.remediation_steps = report.remediation_steps
    incident.raw_report = report.model_dump()

    for i, event in enumerate(report.timeline_events, start=1):
        db.add(TimelineEvent(incident_id=incident_id, sequence=i, **event.model_dump()))

    for consumer in report.blast_radius_consumers:
        db.add(BlastRadiusConsumer(incident_id=incident_id, **consumer.model_dump()))

    await db.flush()
    return incident_id
```

---

## Task Retry and Failure Handling

| Scenario | Behaviour |
|---|---|
| Agent raises any exception | Celery retries the task automatically (up to 3 times, exponential backoff) |
| All 3 retries exhausted | Task marked FAILED in Redis; incident row updated to `status=failed` via `on_failure` hook |
| Agent returns a LOW-confidence fallback report | Task completes successfully — a fallback report is a valid outcome, not a failure |
| PostgreSQL write fails | Task retries — the incident row creation at the start is idempotent via `incident_id` reuse |

The `on_failure` hook updates the incident status so the dashboard never shows a stuck PROCESSING incident:

```python
@celery_app.task(... on_failure=mark_incident_failed)
def rca_task(...): ...

def mark_incident_failed(exc, task_id, args, kwargs, einfo):
    # Best-effort: update the incident row to status=failed
    asyncio.run(_mark_failed(kwargs.get("table_fqn"), str(exc)))
```

---

## Redis Connection Config

```python
# Broker: task queue
CELERY_BROKER_URL = "redis://redis:6379/0"

# Result backend: task state and return values
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
```

Two separate Redis DB indexes are used to keep the task queue and result store cleanly separated.

---

## Concurrency and Queue Strategy

- `worker_prefetch_multiplier=1` — the worker fetches one task at a time, preventing long tasks from blocking the queue
- MVP uses a single default queue (`celery`)
- One Celery worker process runs in the `worker` container
- The worker is started with `celery -A worker.celery_app worker --loglevel=info --concurrency=2`
- Concurrency of 2 allows two simultaneous RCA runs without overloading the demo machine

---

## Logging Within Tasks

Task lifecycle events are logged with `structlog`:

```python
logger.info("rca_task_started", table_fqn=table_fqn, task_id=self.request.id)
logger.info("rca_task_complete", incident_id=str(incident_id), duration_ms=elapsed)
logger.error("rca_task_failed", error=str(exc), table_fqn=table_fqn)
```

All logs are JSON-formatted in the worker container (same `structlog` config as the app).

---

## Environment Variables

Read via `app.config.settings`:
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `DATABASE_URL`

The worker container uses the same `.env` file as the app container. Both are built from the same `Dockerfile` with different `CMD` instructions:

```dockerfile
# App container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Worker container
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
```
