# AGENTS.md

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 19, 2026

---

## Purpose

This file is the **entry point for every AI coding assistant** working on this project. It is placed at the repository root so that AI tools (Cursor, Windsurf, GitHub Copilot Workspace, Claude, GPT-4, Gemini, etc.) find it automatically on session start.

Read this file completely before reading any other file or writing any code.

---

## Step 1 — Read the Status File First

```
knowledge/agent-sync/ai-project-status.md
```

This is the single source of truth for where development currently stands: current sprint, ticket statuses, what is done, what is in progress, what is blocked. **Do not skip this step.** Every other action depends on knowing where the project is.

---

## Step 2 — Read the Rules File

```
knowledge/agent-sync/ai-rules.md
```

This defines all non-negotiable rules: locked architectural decisions, module boundary constraints, file placement rules, code style rules, test rules, and what is out of scope. Violations are not acceptable regardless of how reasonable they may seem.

---

## Step 3 — Orient with the Project Summary

```
knowledge/project-understanding/project-summary.md
```

A full orientation to the project — what it does, why it exists, how the 5 modules relate, the tech stack rationale, the 5-sprint plan, and what documents to read for specific questions. Read this if you are new to the project or returning after a gap.

---

## Step 4 — Read the Relevant Service Doc Before Touching Any File

Before modifying any file, read the service doc that owns it:

| File location | Read this service doc |
|---|---|
| `app/` | `knowledge/services/app.md` |
| `agent/` | `knowledge/services/agent.md` |
| `worker/` | `knowledge/services/worker.md` |
| `om_client/` | `knowledge/services/om-client.md` |

---

## Project Structure

```
datalineage-doctor/
│
├── AGENTS.md                          ← You are here
│
├── app/                               # FastAPI HTTP server
│   ├── main.py                        # App factory + lifespan
│   ├── config.py                      # pydantic-settings — ONLY env var reads
│   ├── database.py                    # SQLAlchemy async engine + session factory
│   ├── dependencies.py                # FastAPI Depends() helpers
│   ├── models/                        # SQLAlchemy ORM models
│   ├── schemas/                       # Pydantic request/response schemas
│   ├── routers/                       # One file per route group
│   └── services/                      # Business logic (incident_store, metrics)
│
├── agent/                             # LLM reasoning loop
│   ├── loop.py                        # run_rca_agent() — the tool-calling while loop
│   ├── prompts.py                     # SYSTEM_PROMPT + build_user_message()
│   ├── parser.py                      # Parses LLM final message → RCAReport
│   ├── notifications.py               # Slack + OM incident creation
│   ├── tools/                         # Tool handlers + registry
│   │   ├── registry.py                # RCA_TOOLS list + TOOL_HANDLERS dict + dispatch()
│   │   ├── lineage.py                 # get_upstream_lineage, calculate_blast_radius
│   │   ├── quality.py                 # get_dq_test_results
│   │   ├── pipeline.py                # get_pipeline_entity_status
│   │   ├── ownership.py               # get_entity_owners
│   │   └── history.py                 # find_past_incidents (queries local DB)
│   └── schemas/
│       ├── report.py                  # RCAReport, TimelineEventInput, BlastRadiusConsumerInput
│       └── tool_outputs.py            # Typed return shapes per tool
│
├── worker/                            # Celery task management
│   ├── celery_app.py                  # Celery app instance + config
│   ├── tasks.py                       # rca_task() — the only task in MVP
│   └── persistence.py                 # save_incident() two-phase DB write
│
├── om_client/                         # OpenMetadata REST API client
│   ├── client.py                      # OMClient — async context manager, auth, _get()/_post()
│   ├── lineage.py                     # get_upstream_lineage(), get_downstream_lineage()
│   ├── quality.py                     # get_dq_test_results()
│   ├── pipeline.py                    # get_pipeline_status()
│   ├── ownership.py                   # get_entity_owners()
│   ├── incidents.py                   # create_incident()
│   └── schemas/                       # Typed OM response models
│
├── dashboard/                         # Web UI
│   ├── static/style.css               # Nexus design tokens + base styles
│   └── templates/
│       ├── base.html                  # Layout template
│       ├── incidents_list.html        # GET / — incident list
│       └── incident_detail.html       # GET /incidents/{id} — detail + React Flow graph
│
├── tests/                             # pytest test suite
│   ├── conftest.py                    # Fixtures: mock_om_client, async_client, db session
│   ├── test_webhook.py
│   ├── test_agent_loop.py
│   ├── test_tools_lineage.py
│   ├── test_tools_quality.py
│   ├── test_tools_pipeline.py
│   ├── test_tools_ownership.py
│   ├── test_tools_history.py
│   ├── test_om_client.py
│   └── test_incident_store.py
│
├── scripts/
│   ├── seed_demo.py                   # Idempotent OM demo data seeder
│   ├── trigger_demo.py                # Fires a testCaseFailed webhook
│   ├── wait_for_om.py                 # Polls OM until healthy
│   └── wait_for_incident.py           # Polls app until latest incident is complete
│
├── alembic/                           # Database migrations
│   ├── env.py
│   └── versions/
│
├── grafana/                           # Grafana provisioning (Sprint 4)
│   ├── provisioning/
│   └── dashboards/
│
├── knowledge/                         # Project knowledge base (READ BEFORE CODING)
│   ├── BRD.md
│   ├── SRS.md
│   ├── project-features.md
│   ├── development-guideline.md
│   ├── deployment.md
│   ├── architecture/
│   │   ├── how-services-connect.md
│   │   ├── data-model.md
│   │   └── rca-agent-architecture.md
│   ├── services/
│   │   ├── app.md
│   │   ├── agent.md
│   │   ├── worker.md
│   │   └── om-client.md
│   ├── reference/
│   │   ├── api-spec.md
│   │   ├── code-examples.md
│   │   └── rca-domain-data.md
│   ├── agent-sync/
│   │   ├── ai-rules.md                ← Rules for AI assistants
│   │   └── ai-project-status.md       ← Current sprint + ticket statuses
│   ├── sprint-tickets/
│   │   ├── sprint-1.md
│   │   ├── sprint-2.md
│   │   ├── sprint-3.md
│   │   └── sprint-4.md
│   ├── sprint-progress/
│   │   └── sprint-1-progress.md
│   └── project-understanding/
│       └── project-summary.md
│
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .env                               # gitignored
├── Makefile
├── pyproject.toml
└── README.md
```

---

## Module Dependency Rules (Enforced)

```
app/        → worker/ (via Celery .delay() only — no direct imports)
worker/     → agent/
agent/      → om_client/
om_client/  → OpenMetadata REST API

No reverse imports. No cross-boundary imports.
```

---

## Common Commands

```bash
make dev       # Start full Docker Compose stack
make stop      # Stop all containers
make clean     # Full reset — removes all Docker volumes
make migrate   # Apply Alembic migrations
make test      # Run pytest
make lint      # Run ruff check
make demo      # Seed + trigger + wait + open browser (Sprint 4+)
make logs      # Tail app + worker logs
make shell     # Open shell in app container
```

---

## Local Endpoints (when stack is running)

| URL | What |
|---|---|
| `http://localhost:8000` | Dashboard — incidents list |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/metrics` | Prometheus metrics |
| `http://localhost:8585` | OpenMetadata UI |
| `http://localhost:3000` | Grafana (admin/admin) — Sprint 4+ |

---

## Quick Navigation — Knowledge Base

| I need to... | Read... |
|---|---|
| Know the current sprint status | `knowledge/agent-sync/ai-project-status.md` |
| Know the rules for this project | `knowledge/agent-sync/ai-rules.md` |
| Add a new RCA tool | `knowledge/services/agent.md` → `knowledge/reference/code-examples.md` |
| Add a new API route | `knowledge/services/app.md` → `knowledge/reference/code-examples.md` |
| Understand the database schema | `knowledge/architecture/data-model.md` |
| Understand service boundaries | `knowledge/architecture/how-services-connect.md` |
| Check API request/response contracts | `knowledge/reference/api-spec.md` |
| Understand what the agent reasons about | `knowledge/reference/rca-domain-data.md` |
| Check coding standards | `knowledge/development-guideline.md` |
| Run or deploy the project | `knowledge/deployment.md` |
| See what is in/out of MVP scope | `knowledge/project-features.md` |
| Find canonical code patterns | `knowledge/reference/code-examples.md` |
| See current sprint tickets | `knowledge/sprint-tickets/sprint-1.md` |

---

## End of Session Checklist

At the end of every working session, before closing:

1. Update ticket statuses in `knowledge/agent-sync/ai-project-status.md`
2. Update `knowledge/sprint-progress/sprint-1-progress.md` (or current sprint progress file)
3. If a new pattern was introduced, add it to `knowledge/reference/code-examples.md`
4. If a new doc/file was created that isn't in this file's structure tree, add it
5. If any architectural decision was made, add it to the relevant `knowledge/architecture/` doc
