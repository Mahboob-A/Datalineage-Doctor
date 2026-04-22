# Sprint 2 Progress Log

## 2026-04-22

### Scope Reviewed
- Plan: `knowledge/plan/agent-plan-sprint-2-1.md`
- Tickets: `knowledge/sprint-tickets/sprint-2.md`
- Progress baseline: this Sprint 2 progress log
- Verification performed this session:
  - `uv run pytest tests -q` -> `42 passed, 1 warning`
  - `uv run ruff check .` -> passed
  - `uv run python scripts/seed_demo.py` -> succeeded
  - `uv run python scripts/seed_demo.py` rerun -> idempotent success
  - refreshed `OM_JWT_TOKEN` in `.env`
  - recreated `app` and `worker` containers to reload `.env`
  - `uv run python scripts/trigger_demo.py` -> webhook queued successfully
  - final live smoke run completed with a real HIGH-confidence RCA

### Sprint 2 Plan Completion Snapshot
- Plan scope considered: DLD-011 through DLD-019 (9 tickets total).
- Fully completed tickets: 9/9 (**100%**) -> DLD-011 through DLD-019.
- Blocked tickets: 0/9 (**0%**).
- Overall sprint status: Sprint 2 is complete.

### What Worked
- Docker Compose runtime and OpenMetadata stack are healthy.
- `scripts/seed_demo.py` passes its live validation gate and reruns idempotently at `created=0 existing=36 failed=0`.
- Gemini 2.5 Flash successfully completes the live RCA loop through the existing OpenAI-compatible integration path.
- OpenMetadata-backed tool calls succeed live after refreshing the JWT and recreating the service containers.
- Webhook queueing, Celery worker execution, incident persistence, and `/metrics` work in the live environment.

### Temporary Failure During Closure
- After the AI provider switch (from cerebras to Gemini) and stack restart, the OpenMetadata JWT in `.env` was stale.
- Live OM API calls returned `401 Unauthorized` until `OM_JWT_TOKEN` was refreshed and the `app` and `worker` containers were recreated.

### Ticket-by-Ticket Status Against Plan
| Ticket | Planned Outcome | Current Status | Notes |
|---|---|---|---|
| DLD-011 | Real tool-calling LLM loop + parser + retries + tool call logs | Done | `agent/loop.py` and `agent/parser.py` implemented; automated tests passing. |
| DLD-012 | Upstream lineage tool + OM lineage client | Done | `om_client/lineage.py` and `agent/tools/lineage.py` implemented. |
| DLD-013 | DQ test history tool + OM quality client | Done | `om_client/quality.py` and `agent/tools/quality.py` implemented. |
| DLD-014 | Pipeline status tool + OM pipeline client | Done | `om_client/pipeline.py` and `agent/tools/pipeline.py` implemented. |
| DLD-015 | Ownership tool + OM ownership client | Done | `om_client/ownership.py` and `agent/tools/ownership.py` implemented. |
| DLD-016 | Blast radius traversal + sorting | Done | Downstream lineage support implemented and covered by lineage tool tests. |
| DLD-017 | Past incident lookup from local DB | Done | `agent/tools/history.py` implemented and tested. |
| DLD-018 | Idempotent demo seed script for OM topology | Done | Live OM validation passed; rerun now ends at `created=0 existing=36 failed=0`. |
| DLD-019 | Real end-to-end smoke run with live LLM and seeded OM | Done | Final live incident completed with HIGH confidence, 4 timeline events, 4 blast-radius consumers, and `/metrics` recorded `rca_requests_total{status="success"} 1.0`. |

### Final DLD-019 Outcome
- Latest live incident: `a7ed0d7d-1784-4a4b-8e1b-18f3bee44ef3`
- Status: `COMPLETE`
- Root cause summary: identified `airflow.ingest_orders_daily` and its `load_orders` task failure as the upstream cause.
- Confidence label: `HIGH`
- Timeline events recorded: `4`
- Blast-radius consumers recorded: `4`
- Worker log result: `Task worker.tasks.rca_task[...] succeeded`
- Metrics confirmation: `rca_requests_total{status="success"} 1.0`

### Completed
- Sprint 2 plan execution delivered the full RCA tool layer from DLD-011 through DLD-017.
- `scripts/seed_demo.py` now seeds the Sprint 2 demo topology and reruns cleanly without duplicates.
- `scripts/trigger_demo.py` is aligned to the Sprint 2 failure scenario for `null_check_order_id`.
- The live provider path is now Gemini 2.5 Flash.
- The cached duplicate-tool-call regression test was aligned with current `agent/loop.py` behavior.
- Automated quality gates verified this session:
  - `uv run pytest tests -q` -> `42 passed, 1 warning`
  - `uv run ruff check .` -> passed

### In Progress
- No Sprint 2 work remains in progress.

### Blockers
- No open Sprint 2 blockers remain.

### Validation Notes
- The repo now verifies at `42 passed` tests.
- The acceptance gate that previously failed due provider context limits is now cleared on Gemini 2.5 Flash.
- Sprint 3 planning in `knowledge/plan/agent-plan-sprint-3-1.md` is now unblocked.

### Next Step
1. Start Sprint 3 using `knowledge/plan/agent-plan-sprint-3-1.md`.

### Recommended Sprint Framing
- Sprint 2 is best described as **completed with live Gemini-backed RCA validation**.
