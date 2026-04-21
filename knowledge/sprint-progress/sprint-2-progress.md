# Sprint 2 Progress Log

## 2026-04-21

### Scope Reviewed
- Plan: `knowledge/plan/agent-plan-sprint-2-1.md`
- Tickets: `knowledge/sprint-tickets/sprint-2.md`
- Progress baseline: this Sprint 2 progress log
- Verification performed this session:
  - `uv run pytest tests -q` -> `40 passed, 1 warning`
  - `uv run ruff check .` -> passed
  - `make dev` -> local stack started successfully
  - `uv run python scripts/seed_demo.py` -> succeeded
  - `uv run python scripts/seed_demo.py` rerun -> idempotent success
  - `uv run python scripts/trigger_demo.py` -> webhook queued successfully
  - Live smoke result persisted, but report fell back due LLM context-length failure

### Sprint 2 Plan Completion Snapshot
- Plan scope considered: DLD-011 through DLD-019 (9 tickets total).
- Fully completed tickets: 8/9 (**88.9%**) -> DLD-011 through DLD-018.
- Blocked tickets: 1/9 (**11.1%**) -> DLD-019 remains blocked by the live LLM provider context-length ceiling.
- Overall sprint status: Sprint 2 engineering and runtime setup are complete through the seed/idempotency gate; Sprint 2 is not closed because the real-agent smoke run still falls back under live provider constraints.

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
| DLD-019 | Real end-to-end smoke run with live LLM and seeded OM | Blocked | Queue, worker, persistence, OM tools, and metrics path all run, but the live RCA still falls back because the provider rejects the message history with `context_length_exceeded`. |

### Completed
- Sprint 2 plan execution has delivered the full core tool layer from DLD-011 through DLD-017.
- Real agent loop implemented with parser integration, retry behavior, tool dispatch, and tool-call logging.
- All six Sprint 2 RCA tools are implemented:
  - `get_upstream_lineage`
  - `get_dq_test_results`
  - `get_pipeline_entity_status`
  - `get_entity_owners`
  - `calculate_blast_radius`
  - `find_past_incidents`
- `scripts/seed_demo.py` was expanded to seed the Sprint 2 demo topology, including services, tables, lineage, pipeline state, and DQ test cases.
- `scripts/trigger_demo.py` is aligned to the Sprint 2 failure scenario for `null_check_order_id`.
- `scripts/seed_demo.py` was fixed for true idempotency by detecting existing lineage edges and existing pipeline status before writing.
- Local OM access was restored by starting the Compose stack and refreshing `OM_JWT_TOKEN` in `.env`.
- `agent/loop.py` was improved to retry compactly after malformed/truncated outputs and to cache duplicate tool calls within a single RCA run.
- Automated quality gates verified this session:
  - `uv run pytest tests -q` -> `40 passed, 1 warning`
  - `uv run ruff check .` -> passed

### In Progress
- No Sprint 2 implementation tickets remain in progress. The remaining work is concentrated in the DLD-019 smoke-test closure.

### Blockers
- The stack and OM runtime are reachable now, but the live LLM provider still fails during DLD-019 with:
  - `context_length_exceeded`
  - `Current length is 12793 while limit is 8192`
- Latest live smoke outcome:
  - incident persisted with `status=COMPLETE`
  - `root_cause_summary` is fallback text
  - `confidence_label=LOW`
  - `timeline_count=1`
  - `blast_count=0`
- Because of that LLM failure, the smoke run does not satisfy Sprint 2 acceptance criteria for HIGH-confidence non-stub RCA output.

### Validation Notes
- The previous progress entry understated current automated validation coverage; the repo now verifies at `40 passed` tests rather than `36`.
- DLD-018 now passes live validation:
  - first successful seeded run produced `created=8 existing=28 failed=0`
  - idempotency rerun now produces `created=0 existing=36 failed=0`
- `/metrics` now records the queued smoke request path, including `rca_requests_total{status="success"} 1.0`, but the RCA content still fails the report-quality acceptance gate.
- Lint is clean, and focused agent-loop regression tests pass (`tests/test_agent_loop.py`: `6 passed`).
- Sprint 3 planning exists in `knowledge/plan/agent-plan-sprint-3-1.md`, but that plan itself correctly treats Sprint 2 closure as a prerequisite.

### Next Steps To Close Sprint 2
1. Reduce the live RCA message footprint so the provider stays below its 8192-token limit.
2. Prioritize one of these fixes for DLD-019:
   - reduce tool-result payload size passed back into the model
   - cap or gate repeated tool usage more aggressively
   - switch the live smoke run to an OpenAI-compatible model/provider with a larger context window
3. Rerun `uv run python scripts/trigger_demo.py` after the loop/prompt/provider change.
4. Validate the DLD-019 acceptance checks:
   - non-stub root cause summary
   - `confidence_label = HIGH`
   - at least 3 timeline events
   - at least 2 blast radius consumers
   - successful RCA metric increment in `/metrics`
5. Once DLD-019 passes, mark Sprint 2 complete and update:
   - `knowledge/sprint-tickets/sprint-2.md` traceability section
   - `knowledge/agent-sync/ai-project-status.md`
   - this progress log

### Recommended Sprint Framing
- Sprint 2 is best described as **runtime-ready but smoke-test blocked on live LLM limits**.
- The highest-value next action is no longer OpenMetadata setup; it is getting one successful live HIGH-confidence RCA run through the chosen model/provider.
