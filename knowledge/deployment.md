# Deployment Guide

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Deployment Overview

DataLineage Doctor runs entirely in Docker Compose for local development and demo. There is no cloud deployment target for MVP. The entire stack — FastAPI app, Celery worker, Redis, PostgreSQL, and the OpenMetadata platform — runs on a single developer machine.

Production deployment infrastructure (Kubernetes, Helm, cloud provider configuration) is explicitly out of scope for this project.

---

## Docker Compose Stack

The full stack is defined in `docker-compose.yml` at the project root.

### Services

| Service | Image | Role | Internal Port |
|---|---|---|---|
| `app` | Built from `Dockerfile` | FastAPI HTTP server | 8000 |
| `worker` | Built from `Dockerfile` | Celery RCA task worker | — |
| `redis` | `redis:7-alpine` | Celery broker and result backend | 6379 |
| `db` | `postgres:16-alpine` | Local persistence (incidents, reports) | 5432 |
| `openmetadata_server` | `openmetadata/server` | OpenMetadata backend | 8585 |
| `openmetadata_ingestion` | `openmetadata/ingestion` | OpenMetadata ingestion UI | 8080 |
| `elasticsearch` | `elasticsearch:8.x` | OpenMetadata search backend | 9200 |
| `mysql` | `mysql:8` | OpenMetadata metadata store | 3306 |

The OpenMetadata stack (last four services) uses the official OpenMetadata Docker Compose configuration as a base. It is included or referenced via `docker-compose.override.yml`.

---

## Local Development Setup

### Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine + Compose plugin (Linux)
- Python 3.12 with `uv` installed
- Git
- At least 8 GB free RAM (OpenMetadata stack is memory-heavy)

### First-time setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd datalineage-doctor

# 2. Copy environment file and fill in values
cp .env.example .env
# Edit .env — minimum required: LLM_API_KEY, LLM_MODEL, SLACK_WEBHOOK_URL

# 3. Start the full stack
make dev

# 4. Wait for OpenMetadata to be healthy (takes ~2-3 minutes on first start)
# Check: http://localhost:8585 should show the OM login page

# 5. Run database migrations
make migrate

# 6. Verify the app is running
curl http://localhost:8000/health
```

---

## Environment Configuration

All environment variables are documented in `.env.example`. Copy it to `.env` for local use. `.env` is gitignored.

### Required variables

```bash
# LLM Configuration
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.0-flash
LLM_TIMEOUT_SECONDS=90
LLM_MAX_ITERATIONS=15

# PostgreSQL
DATABASE_URL=postgresql+psycopg://dld:dld@db:5432/datalineage_doctor

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# OpenMetadata
OM_BASE_URL=http://openmetadata_server:8585/api
OM_JWT_TOKEN=your-om-jwt-token-here

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
SLACK_ENABLED=true

# App
APP_ENV=development
APP_PORT=8000
LOG_LEVEL=INFO
APP_BASE_URL=http://localhost:8000
```

### Switching LLM providers

To switch from Gemini to another OpenAI-compatible provider, update three variables only:

```bash
# DeepSeek
LLM_API_KEY=your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# Kimi (Moonshot)
LLM_API_KEY=your-moonshot-key
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-8k

# GLM (Zhipu)
LLM_API_KEY=your-zhipu-key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4
```

No code changes are required when switching providers.

---

## Makefile Commands

```makefile
make dev         # Start full Docker Compose stack
make stop        # Stop all containers
make clean       # Stop and remove all volumes (full reset)
make migrate     # Run Alembic migrations
make test        # Run pytest suite
make lint        # Run ruff check and format check
make demo        # Seed OM data, trigger a failure, open dashboard
make logs        # Tail app and worker logs
make shell       # Open a shell in the app container
```

---

## Running the Demo

From a cold start with the stack already running:

```bash
# Step 1: Seed demo entities into OpenMetadata
uv run python scripts/seed_demo.py

# Step 2: Trigger a DQ test failure (fires the webhook)
uv run python scripts/trigger_demo.py

# Step 3: Watch the RCA agent process the incident
make logs

# Step 4: Open the dashboard
open http://localhost:8000
```

Or run all steps at once:

```bash
make demo
```

Within approximately 3 minutes, an incident appears in the dashboard at `http://localhost:8000` with a lineage graph, timeline, blast radius table, and Slack notification.

---

## Database Migrations

Alembic manages all schema changes. Migrations run automatically in `make dev` via an init container, or manually:

```bash
# Apply all pending migrations
make migrate

# Generate a new migration after model changes
docker compose exec app uv run alembic revision --autogenerate -m "description"
```

---

## Health Checks

| Endpoint | Expected response |
|---|---|
| `GET http://localhost:8000/health` | `{"status": "ok"}` |
| `GET http://localhost:8000/metrics` | Prometheus text format |
| `GET http://localhost:8585` | OpenMetadata login page |

---

## Resetting Demo State

To run the demo from a fully clean state:

```bash
make clean        # Removes all Docker volumes
make dev          # Starts fresh stack
make migrate      # Re-applies database schema
make demo         # Re-seeds and triggers
```

---

## Pre-deployment Checklist

Before demo or submission:

- [ ] `.env` is populated with valid API keys
- [ ] `make dev` starts all containers without errors
- [ ] `http://localhost:8585` shows the OpenMetadata UI
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `make migrate` exits with code 0
- [ ] `make test` exits with code 0 (≥ 50 tests passing)
- [ ] `make demo` completes and an incident is visible in the dashboard
- [ ] Slack notification is received (if `SLACK_ENABLED=true`)
- [ ] `/metrics` shows all six required metrics after one demo run

---

## Known Constraints

- The OpenMetadata stack takes 2–3 minutes to become healthy on first start due to Elasticsearch and MySQL initialisation
- Demo requires at least 8 GB RAM; 16 GB recommended when running the full OM stack alongside the app
- `LLM_TIMEOUT_SECONDS` should be set to at least 90 for providers with higher latency (GLM, Kimi on free tier)
- The seed script is idempotent but requires OpenMetadata to be fully healthy before running
