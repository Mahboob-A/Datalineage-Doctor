# AI Project Status

**Project:** DataLineage Doctor
**Version:** 1.0
**Last Updated:** April 21, 2026
**Updated By:** AI Agent

> **Instructions for the AI:** Read this document at the start of every session. It tells you exactly where development stands, what is done, what is in progress, and what is next. After completing any task, remind the engineer to update this document.

---

## Project Overview

DataLineage Doctor is a solo-built hackathon project for the OpenMetadata Hackathon (April 17–26, 2026). It is a FastAPI + Celery application that receives OpenMetadata `testCaseFailed` webhook events, runs an LLM-powered root cause analysis agent, and returns a structured RCA report with timeline, blast radius, and remediation steps. The dashboard is a Jinja2-rendered web UI.

**Submission deadline:** April 26, 2026 (9 days from project start)
**Demo video required:** Yes — 3 to 5 minutes
**Prize target:** 1st place (MacBook)

---

## Tech Stack (Locked)

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| Task queue | Celery + Redis |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| LLM SDK | `openai` (OpenAI-compatible, default: Gemini 2.0 Flash) |
| HTTP client | `httpx` async |
| Package manager | `uv` |
| Config | `pydantic-settings` |
| Logging | `structlog` |
| Retry | `tenacity` |
| Testing | `pytest` + `pytest-asyncio` |
| Templates | Jinja2 |
| Lineage graph UI | React Flow (CDN) |
| Metrics | `prometheus_client` |
| Containerisation | Docker Compose |

---

## Current Sprint

**Sprint 2 — Agent Tools** (April 19–20)
**Goal:** Build and test all 6 real RCA tools and move from stubbed analysis to real OpenMetadata-backed reasoning.

---

## Sprint 1 Ticket Status

| Ticket | Title | Status |
|---|---|---|
| DLD-001 | Project scaffold + Docker Compose | ✅ Done |
| DLD-002 | Config + pydantic-settings | ✅ Done |
| DLD-003 | SQLAlchemy models + Alembic init | ✅ Done |
| DLD-004 | Webhook endpoint (POST /webhook/openmetadata) | ✅ Done |
| DLD-005 | Celery app + rca_task stub | ✅ Done |
| DLD-006 | OMClient skeleton + auth | ✅ Done |
| DLD-007 | Agent loop skeleton (stub tools, mock LLM) | ✅ Done |
| DLD-008 | Jinja2 dashboard — incidents list page | ✅ Done |
| DLD-009 | Health + metrics endpoints | ✅ Done |
| DLD-010 | make dev + make demo working end-to-end | ✅ Done (local validation) |

---

## Upcoming Sprints (Preview)

**Sprint 2 — Agent Tools** (April 19–20)
Build and test all 6 real RCA tools (lineage, DQ history, pipeline status, ownership, blast radius, past incidents). Agent produces real reports against the seeded OM data.

**Sprint 3 — Dashboard + Notifications** (April 21–22)
React Flow lineage graph, incident detail page, timeline UI, Slack notification, OM incident creation.

**Sprint 4 — Observability + Polish** (April 23–24)
Grafana dashboard wired to Prometheus metrics, seed script, trigger script, `make demo` one-command flow, README.

**Sprint 5 — Demo + Submission** (April 25–26)
Demo video recording, submission write-up, final README review.

---

## Done (Across All Sprints)

- Sprint 1 completed: DLD-001 through DLD-010.

---

## In Progress

- Sprint 2 remains open pending runtime validation gates.
- DLD-011 through DLD-017 are implemented and locally validated.
- DLD-018 is now complete with live OpenMetadata validation and an idempotent rerun.
- DLD-019 smoke test remains blocked by the live LLM provider context-length limit, not by OM/runtime availability.

---

## Blocked

- The local stack is running and OpenMetadata is reachable, but the live RCA smoke run still fails with provider error `context_length_exceeded`.
- Sprint 2 cannot close until DLD-019 produces a real HIGH-confidence report rather than the fallback LOW-confidence error report.

---

## Key Files and Their Current State

| File | State | Notes |
|---|---|---|
| `docker-compose.yml` | ✅ Created | DLD-001 |
| `Dockerfile` | ✅ Created | DLD-001 |
| `app/main.py` | ✅ Created | DLD-001 |
| `app/config.py` | ✅ Created | DLD-002 |
| `app/models/incident.py` | ✅ Created | DLD-003 |
| `alembic/` | ✅ Created | DLD-003 |
| `app/routers/webhook.py` | ✅ Created | DLD-004 |
| `worker/celery_app.py` | ✅ Created | DLD-005 |
| `worker/tasks.py` | ✅ Created | DLD-005 |
| `om_client/client.py` | ✅ Created | DLD-006 |
| `agent/loop.py` | ✅ Created | DLD-007 |
| `dashboard/templates/` | ✅ Created | DLD-008 |
| `app/routers/health.py` | ✅ Created | DLD-009 |
| `Makefile` | ✅ Created | DLD-010 |
| `scripts/seed_demo.py` | ✅ Created | Sprint 2 seeding implementation updated (services/tables/lineage/pipeline status/DQ tests) |
| `scripts/trigger_demo.py` | ✅ Created | Sprint 2 demo trigger payload aligned (`null_check_order_id`) |

---

## Decisions Made This Session

_(Update this section at the end of each working session with any decisions made that are not already captured in other knowledge docs.)_

- Sprint 1 completed via agent-plan-sprint-1-1.
- Used local `uv` validation (`pytest` + `ruff`) due Docker daemon unavailability.
- Completed 21 tests passing locally and lint clean.
- Sprint 2 core tooling (DLD-011 to DLD-017) remains complete, with local lint passing and `40` tests passing.
- Seed and trigger scripts are implemented for Sprint 2 demo flow; DLD-018 now passes live OM validation and idempotency.
- Local runtime was restored by starting Docker Compose and refreshing the OpenMetadata JWT used by the repo.
- The current Sprint 2 blocker is the live LLM provider's 8192-token context ceiling during DLD-019, even after agent-loop compaction improvements.

---

## How to Update This Document

At the end of every working session:

1. Change ticket statuses: `🔲 Not started` → `🔄 In progress` → `✅ Done`
2. Move completed tickets to the **Done** section
3. Update the **Key Files** table state column
4. Add any new decisions to **Decisions Made This Session**
5. If a sprint is complete, update **Current Sprint** to the next sprint

**Status legend:**
- 🔲 Not started
- 🔄 In progress
- ✅ Done
- 🚫 Blocked

---

## Quick Links (Knowledge Base)

| Need to... | Read... |
|---|---|
| Understand the full feature set | `knowledge/project-features.md` |
| Check what is in/out of scope | `knowledge/SRS.md` FR sections |
| Implement a new tool | `knowledge/services/agent.md` + `knowledge/reference/code-examples.md` |
| Add a new route | `knowledge/services/app.md` + `knowledge/reference/code-examples.md` |
| Write a DB query | `knowledge/services/worker.md` + `knowledge/architecture/data-model.md` |
| Understand module boundaries | `knowledge/architecture/how-services-connect.md` |
| Check the API contract | `knowledge/reference/api-spec.md` |
| Understand the domain | `knowledge/reference/rca-domain-data.md` |
| Check coding standards | `knowledge/development-guideline.md` |
| Understand deployment | `knowledge/deployment.md` |
| Know what rules apply to AI | `knowledge/agent-sync/ai-rules.md` |
