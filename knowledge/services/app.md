# App Service Implementation Guide

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## What This Service Owns

The `app/` directory is the FastAPI HTTP server. It owns all inbound HTTP concerns: the webhook receiver, the Jinja2-rendered dashboard, the health endpoint, and the Prometheus metrics endpoint. It does not own agent logic, task execution, or OpenMetadata API calls. It reads from PostgreSQL to serve the dashboard and enqueues tasks to Redis via Celery.

---

## Directory Structure

```
app/
├── __init__.py
├── main.py                  # FastAPI app factory, router registration, lifespan
├── config.py                # Single source of all env var reads via pydantic-settings
├── dependencies.py          # FastAPI dependency injection (DB session, etc.)
├── database.py              # SQLAlchemy async engine and session factory
│
├── models/                  # SQLAlchemy ORM models (single source of truth for schema)
│   ├── __init__.py
│   ├── incident.py          # Incident, IncidentStatus, ConfidenceLabel
│   ├── timeline_event.py    # TimelineEvent
│   ├── blast_radius.py      # BlastRadiusConsumer
│   └── tool_call_log.py     # ToolCallLog
│
├── schemas/                 # Pydantic request/response schemas (API contract layer)
│   ├── __init__.py
│   ├── webhook.py           # WebhookPayload, WebhookResponse
│   └── incident.py          # IncidentListItem, IncidentDetail
│
├── routers/                 # One file per route group
│   ├── __init__.py
│   ├── webhook.py           # POST /webhook/openmetadata
│   ├── dashboard.py         # GET /, GET /incidents/{id}
│   └── health.py            # GET /health, GET /metrics
│
└── services/                # Business logic called by routers (thin layer)
    ├── __init__.py
    ├── incident_store.py    # CRUD helpers for incident queries
    └── metrics.py           # Prometheus registry and metric definitions
```

---

## Key Patterns

### App Factory — `main.py`

The FastAPI app is created via a factory function, not at module level. This makes testing easier (create a fresh app per test).

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routers import webhook, dashboard, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

def create_app() -> FastAPI:
    app = FastAPI(title="DataLineage Doctor", lifespan=lifespan)
    app.include_router(webhook.router)
    app.include_router(dashboard.router)
    app.include_router(health.router)
    return app

app = create_app()
```

### Config — `config.py`

The only module that reads environment variables. Every other module imports from here.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_api_key: str
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: int = 90
    llm_max_iterations: int = 15

    # Database
    database_url: str

    # Redis / Celery
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    # OpenMetadata
    om_base_url: str
    om_jwt_token: str
    om_max_lineage_depth: int = 3

    # Notifications
    slack_webhook_url: str = ""
    slack_enabled: bool = True

    # App
    app_env: str = "development"
    log_level: str = "INFO"

settings = Settings()
```

`settings` is a module-level singleton. Import it as `from app.config import settings`.

### Database Session — `dependencies.py`

```python
from app.database import AsyncSessionLocal

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
```

Inject into route handlers as `db: AsyncSession = Depends(get_db)`.

### Webhook Router — `routers/webhook.py`

The webhook handler validates, filters, and enqueues. It never touches agent logic.

```python
@router.post("/webhook/openmetadata", status_code=202)
async def receive_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    if payload.event_type != "testCaseFailed":
        return WebhookResponse(status="ignored")

    task = rca_task.delay(
        table_fqn=payload.entity.fqn,
        test_case_fqn=payload.entity.name,
        triggered_at=payload.timestamp.isoformat(),
    )
    return WebhookResponse(status="queued", task_id=task.id)
```

### Dashboard Router — `routers/dashboard.py`

Routes render Jinja2 templates. No JSON responses from dashboard routes.

```python
@router.get("/", response_class=HTMLResponse)
async def incidents_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
):
    incidents = await incident_store.list_incidents(db, page=page, page_size=20)
    return templates.TemplateResponse(
        "incidents_list.html",
        {"request": request, "incidents": incidents, "page": page},
    )
```

### Error Handling

Unhandled exceptions return a JSON error body, never a raw traceback. Registered via `@app.exception_handler`.

```python
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "validation_error", "detail": exc.errors()},
    )
```

### Metrics — `services/metrics.py`

Prometheus metrics are defined once here and imported wherever they are incremented. The `/metrics` endpoint uses `prometheus_client.generate_latest()`.

---

## Environment Variables

All read via `app/config.py`. See `knowledge/deployment.md` for the full list with descriptions.

Variables this service reads directly at runtime:
- `DATABASE_URL`
- `CELERY_BROKER_URL`
- `APP_ENV`
- `LOG_LEVEL`

All LLM, OM, and Slack variables are read by the worker and agent modules, not by the app at request time.

---

## Extension Rules

- New routes go in a new file under `app/routers/` and are registered in `main.py`
- New database queries go in `app/services/incident_store.py`, not inline in route handlers
- New Pydantic schemas go in `app/schemas/`
- New ORM models go in `app/models/` and must have a corresponding Alembic migration
- Never call `om_client` from any file in `app/` — that boundary belongs to `agent/` and `worker/`
- Never import from `agent/` or `worker/` in `app/` — the app communicates with the worker via Celery task calls only
