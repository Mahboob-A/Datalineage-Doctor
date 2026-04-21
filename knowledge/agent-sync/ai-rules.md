# AI Rules

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 18, 2026
**Status:** Approved

---

## Purpose

This document defines the rules an AI coding assistant must follow when working on this project. Every rule is non-negotiable unless explicitly overridden by the engineer in the current session. Read this document fully before touching any file in the repository.

---

## 1. Source of Truth Hierarchy

When there is any conflict between documents, follow this priority order:

1. **This document** (`ai-rules.md`) — overrides everything
2. **`knowledge/architecture/`** — architectural decisions are locked
3. **`knowledge/services/`** — service implementation patterns are locked
4. **`knowledge/reference/`** — API contracts and code examples are canonical
5. **`knowledge/SRS.md`** — functional requirements define what must be built
6. **`knowledge/project-features.md`** — feature scope defines what is in/out of MVP
7. **`knowledge/development-guideline.md`** — coding standards apply everywhere

If you are unsure which document governs a decision, ask before acting.

---

## 2. Locked Architectural Decisions

These decisions are final. Do not propose alternatives, do not refactor away from them, do not add comments suggesting they should be changed.

| Decision | Locked choice | Do not suggest |
|---|---|---|
| Agent framework | No framework — plain `while` loop in `loop.py` | LangChain, LangGraph, CrewAI, AutoGen, or any other agent framework |
| LLM integration | `openai` SDK with `base_url` override | `anthropic`, `google-generativeai`, `litellm`, or direct HTTP |
| Task queue | Celery + Redis | RQ, Dramatiq, APScheduler, FastAPI BackgroundTasks for agent work |
| ORM | SQLAlchemy 2.0 async with typed `Mapped[]` | Django ORM, Tortoise ORM, raw SQL, synchronous SQLAlchemy |
| HTTP client | `httpx` async | `aiohttp`, `requests`, `urllib` |
| Migrations | Alembic | Direct `CREATE TABLE`, SQLAlchemy `create_all()` in production |
| Package manager | `uv` | `pip`, `poetry`, `pipenv`, `conda` |
| Config management | `pydantic-settings` with `.env` | `python-decouple`, `dynaconf`, `os.environ` direct reads |
| Logging | `structlog` (JSON output) | Python `logging` module directly, `loguru`, `print()` |
| Retry logic | `tenacity` | Manual retry loops, `backoff`, `retry` library |
| Testing | `pytest` + `pytest-asyncio` | `unittest`, `nose` |

---

## 3. Module Boundary Rules

These boundaries are enforced. Never write code that violates them.

```
app/        ──▶  worker/ (via Celery .delay() only)
                 NO direct imports from agent/ or om_client/

worker/     ──▶  agent/
                 NO direct HTTP calls to OpenMetadata
                 NO route handler logic

agent/      ──▶  om_client/
                 NO Celery task management
                 NO database writes (worker persists the RCAReport)

om_client/  ──▶  OpenMetadata REST API (httpx only)
                 NO imports from app/, agent/, or worker/
```

**Violation test:** If you find yourself writing `from agent.loop import run_rca_agent` inside `app/routers/webhook.py`, you are violating the boundary. The app enqueues a Celery task; it does not call the agent directly.

---

## 4. File Placement Rules

| What you are adding | Where it goes |
|---|---|
| New API route | `app/routers/<name>.py`, registered in `app/main.py` |
| New database query | `app/services/incident_store.py` |
| New Pydantic request/response schema | `app/schemas/<name>.py` |
| New SQLAlchemy model | `app/models/<name>.py` + Alembic migration |
| New RCA tool (schema + handler) | Schema in `agent/tools/registry.py`, handler in `agent/tools/<name>.py` |
| New agent output field | `agent/schemas/report.py` → also update `worker/persistence.py` |
| New OM API call | `om_client/<domain>.py` (new file if no existing domain file fits) |
| New Celery task | `worker/tasks.py` (only one task in MVP; extend that file) |
| New Prometheus metric | `app/services/metrics.py` |
| New test | `tests/test_<module>.py` mirroring the source path |
| New script | `scripts/<name>.py` |

---

## 5. Code Style Rules

These extend `knowledge/development-guideline.md`. Both apply.

- **All new code is async** unless it must be sync (Celery task entry points are sync; their inner `_run()` helpers are async)
- **All function signatures use type hints** — no `Any`, no bare `dict` where a typed schema exists
- **All new classes use dataclasses or Pydantic models** — no plain `dict` as a data container
- **No hardcoded strings for entity types, statuses, or event types** — use enums from `shared/`
- **No `TODO` or `FIXME` comments in committed code** — if it needs doing, it gets a ticket
- **No commented-out code** — delete it, or it was never committed
- **All public functions and classes have docstrings** — one sentence minimum
- **No `print()` anywhere** — use `structlog`
- **No `time.sleep()` in async code** — use `asyncio.sleep()`
- **No mutable default arguments** — use `None` and set the default in the function body

---

## 6. Test Rules

- Every new tool function has at least two tests: one success path, one `{"found": False}` or error path
- Every new API route has at least one test using `httpx.AsyncClient` with `ASGITransport`
- All tests that call tool functions must mock `OMClient` — never hit the live OM API
- The test suite must pass before any commit to `main`
- Test files mirror the source structure: `agent/tools/lineage.py` → `tests/test_tools_lineage.py`
- Use `pytest.mark.asyncio` for all async tests
- Use `pytest.mark.parametrize` for tests with multiple input variants

---

## 7. What Requires a Knowledge Doc Update

When you make any of the following changes, you must also update the relevant knowledge document:

| Change | Document to update |
|---|---|
| Add a new RCA tool | `knowledge/architecture/rca-agent-architecture.md` — tool table |
| Add a new API endpoint | `knowledge/reference/api-spec.md` |
| Add a new database table or column | `knowledge/architecture/data-model.md` |
| Change a module boundary | `knowledge/architecture/how-services-connect.md` |
| Add a new Prometheus metric | `knowledge/reference/api-spec.md` — `/metrics` section |
| Add a new code pattern | `knowledge/reference/code-examples.md` |
| Change a deployment step | `knowledge/deployment.md` |
| Change an env variable | `knowledge/deployment.md` |
| Add a new feature | `knowledge/project-features.md` |

Do not merge a code change that adds a new pattern without documenting it. The knowledge base is the living specification.

---

## 8. What Is Out of Scope (Do Not Build)

The following are explicitly excluded from MVP. Do not implement them, do not scaffold for them, do not leave hooks for them unless the feature request document says otherwise.

- Webhook signature verification (HMAC)
- Authentication on any endpoint
- Multi-tenant support
- Cloud deployment (Kubernetes, Helm, ECS, GCP Cloud Run)
- Email notifications
- Prompt management UI or database-backed prompts
- Multi-agent orchestration (single agent only)
- Real-time WebSocket updates to the dashboard
- Dark mode on the dashboard

These are tagged `[FUTURE]` in `knowledge/project-features.md`. If an engineer asks you to implement one, ask them to confirm it is now in scope before proceeding.

---

## 9. How to Handle Ambiguity

When you encounter an ambiguous requirement or a situation not covered by any document:

1. **Check `knowledge/reference/code-examples.md`** — a canonical example may already exist
2. **Check `knowledge/architecture/rca-agent-architecture.md`** — for anything agent-related
3. **Check `knowledge/SRS.md`** — the functional requirements may clarify the intent
4. **If still ambiguous, ask** — state the ambiguity explicitly and propose two options with trade-offs before implementing either

Never resolve ambiguity by making the simplest possible assumption and moving on silently.

---

## 10. Session Start Checklist

At the start of every new session, before writing any code:

1. Read `knowledge/agent-sync/ai-project-status.md` — understand the current sprint, what is done, what is in progress
2. Read the relevant `knowledge/services/<service>.md` for the service you are about to modify
3. Check `knowledge/reference/code-examples.md` for the pattern you need
4. Confirm the feature is in scope per `knowledge/project-features.md`

Do not skip step 1. The project status document is the single source of truth for where development currently stands.
