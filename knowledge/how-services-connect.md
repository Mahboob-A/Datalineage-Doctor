# How Services Connect

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## System Context

DataLineage Doctor is a single-codebase Python application running as two process types — an HTTP server (`app`) and a background task worker (`worker`) — supported by Redis as the message broker and PostgreSQL as the persistence layer. It integrates with two external systems: OpenMetadata (metadata platform) and Slack (notifications).

All communication is over HTTP or TCP on the local Docker network. No service is publicly exposed except the FastAPI app on port 8000.

---

## Architecture Diagram

```
                        ┌─────────────────────────────────────────────────────┐
                        │                  Docker Network                      │
                        │                                                       │
  OpenMetadata          │   ┌─────────────┐       ┌─────────────────────────┐  │
  (fires webhook) ──────┼──▶│  FastAPI    │       │   Celery Worker         │  │
                        │   │  app:8000   │       │   (worker container)    │  │
  Browser ─────────────▶│   │             │       │                         │  │
  (dashboard)           │   │  /webhook   │──────▶│  rca_task()             │  │
                        │   │  /          │ enqueue│                         │  │
                        │   │  /incidents │       │  ┌─────────────────┐    │  │
                        │   │  /health    │       │  │  RCA Agent      │    │  │
                        │   │  /metrics   │       │  │  (agent/)       │    │  │
                        │   └──────┬──────┘       │  │  tool loop      │    │  │
                        │          │               │  └────────┬────────┘    │  │
                        │          │ read          │           │ HTTP calls  │  │
                        │          ▼               │           ▼             │  │
                        │   ┌─────────────┐       │  ┌─────────────────┐    │  │
                        │   │ PostgreSQL  │◀──────┤  │  OM Client      │    │  │
                        │   │ db:5432     │ write │  │  (om_client/)   │    │  │
                        │   └─────────────┘       │  └────────┬────────┘    │  │
                        │                         │           │             │  │
                        │   ┌─────────────┐       └───────────┼─────────────┘  │
                        │   │   Redis     │◀──────────────────┘                │
                        │   │ redis:6379  │  broker/backend                    │
                        │   └─────────────┘                                    │
                        └─────────────────────────────────────────────────────┘
                                    │                        │
                                    │ HTTP (external)        │ HTTP (external)
                                    ▼                        ▼
                           OpenMetadata               Slack Webhook
                           :8585 (OM server)          (hooks.slack.com)
```

---

## Full Request Flow

This is the complete lifecycle of a data quality incident through the system.

### Step 1 — Webhook received

1. OpenMetadata fires a `POST /webhook/openmetadata` request to the FastAPI app when a DQ test fails.
2. The webhook handler validates the payload (see `FR-WEBHOOK-02`).
3. If the event type is not `testCaseFailed`, the handler returns `202 {"status": "ignored"}` immediately.
4. If valid, the handler enqueues an `rca_task` to Redis via Celery and returns `202 {"status": "queued", "task_id": "..."}`.
5. The handler returns before any agent processing begins.

### Step 2 — Celery worker picks up the task

1. The Celery worker process (running in the `worker` container) polls Redis and picks up the `rca_task`.
2. The task extracts the `table_fqn` and `test_case_fqn` from the webhook payload.
3. The task calls `run_rca_agent(table_fqn, test_case_fqn)` from the `agent` module.

### Step 3 — RCA agent reasons

1. The agent builds an initial `messages` list with the system prompt and the incident context.
2. The agent calls the LLM (`openai.chat.completions.create`) with `tools=RCA_TOOLS`.
3. The LLM returns tool calls. The agent dispatches each tool call to the tool registry.
4. Each tool in the registry calls `om_client` methods, which make authenticated HTTP requests to OpenMetadata.
5. Tool results are appended to `messages` and the loop continues.
6. When the LLM returns `finish_reason == "stop"`, the agent parses the final message into a structured `RCAReport`.

### Step 4 — Report persisted

1. The `RCAReport` is written to PostgreSQL by the worker task.
2. `timeline_events` and `blast_radius_consumers` are written as related rows.

### Step 5 — Notifications sent

1. The worker sends a Slack message via HTTP POST to `SLACK_WEBHOOK_URL`.
2. The worker creates an OpenMetadata incident entity via `om_client`.
3. Both notification calls are fire-and-forget — failures are logged but do not fail the task.

### Step 6 — Dashboard read

1. A user opens `http://localhost:8000` in a browser.
2. The FastAPI app queries PostgreSQL and renders the incidents list via Jinja2.
3. The user clicks an incident; the detail page queries the incident and its related events and consumers.
4. The page renders a React Flow graph from the lineage data stored in the incident record.

---

## Service and Module Boundaries

| Boundary | Rule |
|---|---|
| HTTP-facing code | Lives in `app/` only |
| Agent logic and tools | Lives in `agent/` only |
| Celery task definitions | Lives in `worker/` only |
| OpenMetadata HTTP calls | Lives in `om_client/` only — never call OM API directly from `app/` or `agent/` |
| Database models and queries | Lives in `app/models/` and accessed from `worker/` tasks |
| Templates and static assets | Lives in `dashboard/` |
| Shared constants and enums | Lives in `shared/` |

No module may import from another service's internals. The dependency direction is:

```
worker  →  agent  →  om_client
app     →  (reads DB directly)
agent   →  om_client
```

`worker` imports from `agent`. `agent` imports from `om_client`. `app` does not import from `agent` or `worker`.

---

## Ports and Protocols

| Service | Host port | Container port | Protocol | Notes |
|---|---|---|---|---|
| `app` | 8000 | 8000 | HTTP | FastAPI via Uvicorn |
| `db` | 5433 | 5432 | TCP/PostgreSQL | Host port 5433 avoids conflict with local PG |
| `redis` | 6380 | 6379 | TCP/Redis | Host port 6380 avoids conflict with local Redis |
| `openmetadata_server` | 8585 | 8585 | HTTP | OpenMetadata REST API and UI |
| `openmetadata_ingestion` | 8080 | 8080 | HTTP | OpenMetadata Airflow/ingestion UI |
| `elasticsearch` | — | 9200 | HTTP | Internal to OM stack only |
| `mysql` | — | 3306 | TCP | Internal to OM stack only |

---

## OpenMetadata Integration Boundary

All communication with OpenMetadata goes through `om_client/`. The client:

- Authenticates with a JWT token (`OM_JWT_TOKEN` env var)
- Sets `Authorization: Bearer <token>` on every request
- Uses `httpx` with a shared `AsyncClient` instance
- Retries on HTTP 429, 502, 503, 504 with exponential backoff (max 3 attempts)
- Normalises all OM API responses into typed Python objects before returning

The `agent/` module only calls `om_client` functions. It never constructs HTTP requests itself.

---

## Redis and Celery Interaction

- Redis is the Celery **broker** (queue): `redis://redis:6379/0`
- Redis is also the Celery **result backend**: `redis://redis:6379/1` (separate DB index)
- The FastAPI app enqueues tasks using `.delay()` — it does not share a Celery app instance with the worker at runtime
- Task serialisation uses JSON (not pickle)
- Task results are retained in Redis for 1 hour (sufficient for demo; not a long-term store)

---

## Slack Notification Flow

1. Worker calls `notify_slack(report: RCAReport)` from `agent/notifications.py`
2. The function constructs a Slack Block Kit payload
3. An `httpx` POST is made to `SLACK_WEBHOOK_URL`
4. If `SLACK_ENABLED=false` (e.g., in tests), the call is skipped entirely
5. HTTP errors are caught, logged as warnings, and do not propagate

---

## Failure and Fallback Paths

| Failure scenario | Behaviour |
|---|---|
| LLM API returns error | Task retried up to 3 times; fallback LOW-confidence report generated on final failure |
| OM API returns 5xx | `om_client` retries 3 times with backoff; tool returns a structured error dict; agent reasons with partial data |
| OM API returns 404 for entity | Tool returns `{"found": false}`; agent notes the gap and continues |
| Celery task max retries exceeded | Task marked as FAILED in Redis; incident row written with `status=failed` |
| Slack POST fails | Logged as warning; task continues and completes normally |
| OM incident creation fails | Logged as warning; task continues and completes normally |
| PostgreSQL unreachable | Task retried; if persistent, task fails and is logged |

---

## Auth Boundaries

| Boundary | Auth mechanism |
|---|---|
| App → OpenMetadata | JWT Bearer token (`OM_JWT_TOKEN`) |
| App → Slack | Webhook URL contains the secret (no separate auth header) |
| App ← OpenMetadata webhook | No auth on the webhook endpoint in MVP (out of scope — see `[FUTURE]` in `project-features.md`) |
| App → Browser (dashboard) | No auth in MVP |
| App → PostgreSQL | Username/password in `DATABASE_URL` |
| App → Redis | No auth in MVP (local Docker network only) |
