# Code Examples

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Purpose

This document contains canonical implementation examples for the patterns used throughout the codebase. When you implement a new feature, look here first. If a pattern you need is not here, implement it consistently with what exists and add it to this document.

---

## 1. Writing a New RCA Tool

A tool is a Python async function that accepts named arguments matching the OpenAI tool schema, plus a `db_session` argument, and returns a plain dict.

### Schema registration — `agent/tools/registry.py`

```python
# Add to RCA_TOOLS list
{
    "type": "function",
    "function": {
        "name": "get_schema_change_history",
        "description": (
            "Returns recent schema change events for a given table FQN. "
            "Use this when a test failure might be caused by a column being "
            "added, removed, or renamed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "table_fqn": {
                    "type": "string",
                    "description": "Fully qualified name of the table."
                },
                "limit": {
                    "type": "integer",
                    "description": "Max events to return. Default 5.",
                    "default": 5
                }
            },
            "required": ["table_fqn"]
        }
    }
}
```

### Handler function — `agent/tools/schema.py` (new file)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from om_client.client import OMClient
import structlog

logger = structlog.get_logger(__name__)

async def get_schema_change_history(
    table_fqn: str,
    limit: int = 5,
    db_session: AsyncSession = None,  # required signature, may be unused
) -> dict:
    async with OMClient() as om:
        raw = await om._get(
            f"/tables/name/{table_fqn}",
            params={"fields": "changeDescription"},
        )

    if not raw.get("found", True):
        return {"found": False, "events": []}

    events = raw.get("changeDescription", {}).get("fieldsUpdated", [])[:limit]
    return {
        "found": True,
        "table_fqn": table_fqn,
        "schema_change_events": [
            {
                "field": e.get("name"),
                "old_value": e.get("oldValue"),
                "new_value": e.get("newValue"),
            }
            for e in events
        ]
    }
```

### Handler registration — `agent/tools/registry.py`

```python
from agent.tools.schema import get_schema_change_history

TOOL_HANDLERS: dict[str, Callable] = {
    ...existing tools...,
    "get_schema_change_history": get_schema_change_history,
}
```

### Tests — `tests/test_tools.py`

```python
@pytest.mark.asyncio
async def test_get_schema_change_history_found(mock_om_client):
    mock_om_client._get.return_value = {
        "fullyQualifiedName": "mysql.default.raw_orders",
        "changeDescription": {
            "fieldsUpdated": [
                {"name": "columns.order_id", "oldValue": "INT", "newValue": "VARCHAR"}
            ]
        }
    }
    result = await get_schema_change_history("mysql.default.raw_orders", limit=5)
    assert result["found"] is True
    assert len(result["schema_change_events"]) == 1
    assert result["schema_change_events"][0]["field"] == "columns.order_id"


@pytest.mark.asyncio
async def test_get_schema_change_history_not_found(mock_om_client):
    mock_om_client._get.return_value = {"found": False}
    result = await get_schema_change_history("mysql.default.missing_table")
    assert result["found"] is False
    assert result["events"] == []
```

---

## 2. Adding a New API Route

### Route handler — `app/routers/status.py` (new file)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.services import incident_store
from app.schemas.incident import IncidentStatusResponse

router = APIRouter(prefix="/status", tags=["status"])

@router.get("/{incident_id}", response_model=IncidentStatusResponse)
async def get_incident_status(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    incident = await incident_store.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return IncidentStatusResponse(
        id=str(incident.id),
        status=incident.status,
        confidence_label=incident.confidence_label,
    )
```

### Register in `app/main.py`

```python
from app.routers import webhook, dashboard, health, status  # add status

def create_app() -> FastAPI:
    app = FastAPI(title="DataLineage Doctor", lifespan=lifespan)
    app.include_router(webhook.router)
    app.include_router(dashboard.router)
    app.include_router(health.router)
    app.include_router(status.router)   # add this line
    return app
```

### Pydantic schema — `app/schemas/incident.py`

```python
class IncidentStatusResponse(BaseModel):
    id: str
    status: IncidentStatus
    confidence_label: ConfidenceLabel | None = None
```

---

## 3. Mocking OMClient in Tests

All tests that call agent tool functions must mock `OMClient`. The mock boundary is the class constructor — patch where it is instantiated in the tool module, not where it is defined.

### `conftest.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_om_client():
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def patched_om_lineage(mock_om_client):
    with patch("agent.tools.lineage.OMClient", return_value=mock_om_client):
        yield mock_om_client

@pytest.fixture
def patched_om_quality(mock_om_client):
    with patch("agent.tools.quality.OMClient", return_value=mock_om_client):
        yield mock_om_client
```

### Usage in a test

```python
@pytest.mark.asyncio
async def test_get_upstream_lineage_returns_nodes(patched_om_lineage):
    patched_om_lineage._get.side_effect = [
        # First call: resolve table ID
        {"id": "abc-123", "fullyQualifiedName": "mysql.default.raw_orders"},
        # Second call: lineage graph
        {
            "nodes": [
                {"id": "xyz-456", "fullyQualifiedName": "mysql.default.source_events",
                 "type": "Table", "service": {"name": "mysql"}}
            ],
            "edges": [
                {"fromEntity": {"id": "xyz-456"}, "toEntity": {"id": "abc-123"}}
            ]
        }
    ]
    result = await get_upstream_lineage("mysql.default.raw_orders", depth=1)
    assert len(result) == 1
    assert result[0].fqn == "mysql.default.source_events"
```

---

## 4. Writing a Database Query

All database queries go in `app/services/incident_store.py`. Never write raw SQLAlchemy queries in route handlers or worker tasks.

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.incident import Incident, IncidentStatus

async def list_incidents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> list[Incident]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Incident)
        .order_by(Incident.triggered_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


async def get_by_id(db: AsyncSession, incident_id: str) -> Incident | None:
    try:
        uid = uuid.UUID(incident_id)
    except ValueError:
        return None
    return await db.get(Incident, uid)


async def get_history_for_table(
    db: AsyncSession,
    table_fqn: str,
    limit: int = 5,
) -> list[Incident]:
    result = await db.execute(
        select(Incident)
        .where(Incident.table_fqn == table_fqn)
        .where(Incident.status == IncidentStatus.COMPLETE)
        .order_by(Incident.triggered_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
```

---

## 5. Structured Logging

Use `structlog` throughout. Never use Python's built-in `logging` directly.

```python
import structlog
logger = structlog.get_logger(__name__)

# Informational event
logger.info("rca_agent_started", table_fqn=table_fqn, iteration=0)

# Warning (non-fatal issue)
logger.warning("om_entity_not_found", table_fqn=table_fqn, endpoint="/tables/name/...")

# Error (task-level failure)
logger.error("rca_task_failed", error=str(exc), table_fqn=table_fqn, task_id=task_id)
```

Key-value arguments produce structured JSON log output in the worker container. Every log entry should include at minimum the relevant `table_fqn` and `task_id` or `incident_id` for traceability.

---

## 6. Incrementing Prometheus Metrics

Import the metric objects from `app/services/metrics.py` and call `.inc()`, `.observe()`, or `.set()` in the relevant location.

```python
from app.services.metrics import (
    rca_requests_total,
    rca_duration_seconds,
    rca_tool_calls_total,
)

# In worker/tasks.py — after successful completion
rca_requests_total.labels(status="success").inc()
rca_duration_seconds.observe(elapsed_seconds)

# In agent/tools/registry.py — after each tool dispatch
rca_tool_calls_total.labels(tool_name=tool_name).inc()
```

---

## 7. Writing a Database Migration

After changing an SQLAlchemy model, generate and apply a migration:

```bash
# Generate (run inside the app container)
docker compose exec app uv run alembic revision --autogenerate -m "add_schema_change_events_table"

# Review the generated file in alembic/versions/
# Edit if autogenerate missed anything (e.g., custom indexes)

# Apply
make migrate
```

**Never edit an existing migration file that has already been applied to any environment.** Always create a new revision.

---

## 8. Seeding Demo Data

The `scripts/seed_demo.py` script creates a realistic demo dataset in OpenMetadata. It is idempotent — running it twice does not create duplicate entities.

```python
# scripts/seed_demo.py — top-level structure
async def seed():
    async with OMClient() as om:
        await create_service(om, "mysql", "MySQL")
        await create_database(om, "mysql.default")
        await create_table(om, "mysql.default.raw_orders", columns=ORDER_COLUMNS)
        await create_table(om, "mysql.default.raw_products", columns=PRODUCT_COLUMNS)
        await create_table(om, "dbt.default.stg_orders", columns=STG_COLUMNS)
        await create_lineage(om, "mysql.default.raw_orders", "dbt.default.stg_orders")
        await create_dq_test(om, "mysql.default.raw_orders", "null_check_order_id")
        print("Demo seed complete.")

asyncio.run(seed())
```

---

## 9. Triggering a Demo Failure

The `scripts/trigger_demo.py` script sends a `testCaseFailed` webhook payload to the local app.

```python
# scripts/trigger_demo.py
import httpx, json, time

payload = {
    "eventType": "testCaseFailed",
    "entityType": "testCase",
    "timestamp": int(time.time() * 1000),
    "entity": {
        "id": "demo-001",
        "name": "null_check_order_id",
        "fullyQualifiedName": "mysql.default.raw_orders.null_check_order_id",
        "entityType": "testCase",
    },
    "changeDescription": {
        "fieldsUpdated": [
            {"name": "testCaseResult", "newValue": "Failed", "oldValue": "Success"}
        ]
    },
}

resp = httpx.post("http://localhost:8000/webhook/openmetadata", json=payload)
print(resp.status_code, resp.json())
```
