# Sprint 2 Tickets — Agent Tools

**Sprint:** 2 of 5
**Goal:** All 6 RCA tools built and tested. Agent produces real reports against seeded OpenMetadata data. End-to-end flow works with a live LLM.
**Dates:** April 19–20, 2026
**Depends on:** Sprint 1 fully complete

---

## DLD-011 — Real Agent Loop (LLM Integration)

**Priority:** P0 — blocks all tool work
**Estimate:** 2 hours
**Depends on:** DLD-007 (skeleton), DLD-006 (OMClient)

### Context
Replace the Sprint 1 stub loop with the real tool-calling loop. The LLM is now called via the `openai` SDK. Tools are still stubs at the start of this sprint — they get replaced one by one in DLD-012 through DLD-017. This ticket wires the loop, the LLM call, and the output parser.

### Acceptance Criteria
- [ ] `agent/loop.py` implements the full `while` loop from `knowledge/services/agent.md`
- [ ] LLM is called via `openai.AsyncOpenAI` with `base_url=settings.llm_base_url`
- [ ] Tool calls are dispatched via `dispatch_tool()` in `registry.py`
- [ ] Tool results are appended to `messages` in correct OpenAI format
- [ ] `finish_reason == "stop"` → parse final message → return `RCAReport`
- [ ] `finish_reason == "tool_calls"` → dispatch all tool calls → continue loop
- [ ] `iteration >= MAX_ITERATIONS` → return fallback LOW-confidence report
- [ ] `agent/parser.py` exists with `parse_rca_report()` using Pydantic `model_validate`
- [ ] Confidence label is always recalculated from score in the parser (never trust the model's label)
- [ ] `tenacity` retry on LLM API calls (3 attempts, exponential backoff)
- [ ] Tool calls are logged to `tool_call_logs` table via `log_tool_call()` helper in `loop.py`
- [ ] Test: `tests/test_agent_loop.py` — mock LLM client, verify loop terminates correctly on "stop" and "tool_calls"

### `agent/parser.py` Shape
```python
def parse_rca_report(content: str) -> RCAReport:
    # 1. Extract JSON block from content (model may wrap in markdown code fences)
    # 2. RCAReport.model_validate(data)
    # 3. Recalculate confidence_label from score
    # 4. Raise RCAParseError on failure (loop sends correction prompt once)
```

---

## DLD-012 — Tool: get_upstream_lineage

**Priority:** P0
**Estimate:** 1.5 hours
**Depends on:** DLD-011, DLD-006

### Context
Build the real `get_upstream_lineage` tool. It resolves the table FQN to an OM entity ID, then queries the lineage API. Returns a list of upstream `LineageNode` objects. See `knowledge/services/om-client.md` for the `_get()` pattern and `knowledge/reference/rca-domain-data.md` for the lineage graph mental model.

### Acceptance Criteria
- [ ] `om_client/lineage.py` has `get_upstream_lineage(table_fqn, depth)` returning `list[LineageNode]`
- [ ] `agent/tools/lineage.py` has the tool handler wrapping the OM client call
- [ ] Returns `[]` gracefully when the entity is not found (404)
- [ ] Depth is capped at `settings.om_max_lineage_depth`
- [ ] `LineageNode` schema: `fqn`, `entity_type`, `service`, `level` (int, distance from root)
- [ ] Tool handler returns a plain dict with key `"upstream_nodes"` containing serialised node list
- [ ] Tests: success (2 upstream nodes), entity not found (empty list), OM API error (error dict returned)

### OM API Call
```
GET /api/v1/lineage/table/{table_id}?upstreamDepth=3&downstreamDepth=0
```
First resolve FQN to ID:
```
GET /api/v1/tables/name/{url_encoded_fqn}
```

---

## DLD-013 — Tool: get_dq_test_results

**Priority:** P0
**Estimate:** 1.5 hours
**Depends on:** DLD-011, DLD-006

### Context
Build the `get_dq_test_results` tool. It fetches the DQ test result history for a given table FQN — the last N runs of all test cases. This lets the agent correlate the failure timestamp with pipeline events.

### Acceptance Criteria
- [ ] `om_client/quality.py` has `get_dq_test_results(table_fqn, limit)` returning `list[DQTestResult]`
- [ ] `agent/tools/quality.py` has the tool handler
- [ ] `DQTestResult` schema: `test_case_fqn`, `result` (Passed/Failed/Aborted), `timestamp`, `test_type`
- [ ] Results are ordered by timestamp descending (most recent first)
- [ ] Returns empty list gracefully when table or test suite not found
- [ ] Tool handler returns `{"test_results": [...serialised results...]}`
- [ ] Tests: success (3 results), not found (empty), mixed pass/fail results

### OM API Call
```
GET /api/v1/dataQuality/testSuites/executionSummary?entityFQN={fqn}
GET /api/v1/dataQuality/testCases?entityFQN={fqn}&limit={limit}&fields=testCaseResult
```

---

## DLD-014 — Tool: get_pipeline_entity_status

**Priority:** P0
**Estimate:** 1.5 hours
**Depends on:** DLD-011, DLD-006

### Context
Build the `get_pipeline_entity_status` tool. Given a pipeline FQN (e.g. `airflow.ingest_orders_daily`), it returns the last run status and timestamp. This is the most direct indicator of a pipeline-caused failure.

### Acceptance Criteria
- [ ] `om_client/pipeline.py` has `get_pipeline_status(pipeline_fqn)` returning `PipelineStatus`
- [ ] `PipelineStatus` schema: `fqn`, `last_run_status` (Successful/Failed/Pending), `last_run_at`, `task_statuses: list[TaskStatus]`
- [ ] `agent/tools/pipeline.py` has the tool handler
- [ ] Returns `{"found": False}` gracefully when pipeline not found
- [ ] Tool handler returns `{"pipeline_status": {...}}`
- [ ] The tool accepts a pipeline FQN as input — the agent infers this from upstream lineage nodes of type `pipeline`
- [ ] Tests: successful pipeline, failed pipeline, not found

### OM API Call
```
GET /api/v1/pipelines/name/{url_encoded_fqn}?fields=pipelineStatus
```

---

## DLD-015 — Tool: get_entity_owners

**Priority:** P1
**Estimate:** 45 minutes
**Depends on:** DLD-011, DLD-006

### Context
Build the `get_entity_owners` tool. Returns the owner(s) of a given entity FQN. Used for the remediation step — the report names who to notify.

### Acceptance Criteria
- [ ] `om_client/ownership.py` has `get_entity_owners(entity_fqn, entity_type)` returning `list[EntityOwner]`
- [ ] `EntityOwner` schema: `name`, `email`, `type` (user/team)
- [ ] `entity_type` accepted values: `table`, `pipeline`, `dashboard`
- [ ] Returns empty list gracefully when entity has no owners
- [ ] `agent/tools/ownership.py` has the tool handler
- [ ] Tool handler returns `{"owners": [...serialised owners...]}`
- [ ] Tests: entity with team owner, entity with no owners, entity not found

### OM API Call
```
GET /api/v1/{entity_type}s/name/{url_encoded_fqn}?fields=owners
```

---

## DLD-016 — Tool: calculate_blast_radius

**Priority:** P0
**Estimate:** 1.5 hours
**Depends on:** DLD-012 (reuses lineage traversal pattern)

### Context
Build the `calculate_blast_radius` tool. It traverses downstream from the failing table and returns all affected consumers. Mirrors `get_upstream_lineage` but in the downstream direction.

### Acceptance Criteria
- [ ] `om_client/lineage.py` extended with `get_downstream_lineage(table_fqn, depth)`
- [ ] `agent/tools/lineage.py` extended with `calculate_blast_radius` handler
- [ ] Returns a list of `BlastRadiusConsumer` items: `entity_fqn`, `entity_type`, `level`, `service`
- [ ] Consumers are sorted by level ascending (direct consumers first)
- [ ] Returns `[]` gracefully when entity not found or has no downstream
- [ ] Tool handler returns `{"blast_radius": [...], "total_affected": N}`
- [ ] Tests: 3 downstream consumers at 2 levels, no downstream (root table is a sink), not found

### OM API Call
```
GET /api/v1/lineage/table/{table_id}?upstreamDepth=0&downstreamDepth=3
```

---

## DLD-017 — Tool: find_past_incidents

**Priority:** P1
**Estimate:** 45 minutes
**Depends on:** DLD-003, DLD-011

### Context
Build the `find_past_incidents` tool. Unlike all other tools, this one queries our local PostgreSQL database — not OpenMetadata. It looks for previous `COMPLETE` incidents on the same table FQN. This helps the agent identify recurring patterns.

### Acceptance Criteria
- [ ] `agent/tools/history.py` queries `incidents` table via SQLAlchemy
- [ ] Returns the last 5 complete incidents for the given `table_fqn`
- [ ] Each result includes: `incident_id`, `triggered_at`, `root_cause_summary`, `confidence_label`
- [ ] Returns `{"past_incidents": [], "count": 0}` when no history exists
- [ ] Tool handler correctly uses the `db_session` parameter
- [ ] Tests: table with 2 past incidents, table with no history

---

## DLD-018 — Demo Seed Script

**Priority:** P0 — required for demo
**Estimate:** 2 hours
**Depends on:** DLD-006, DLD-012 through DLD-016

### Context
Create `scripts/seed_demo.py` that populates OpenMetadata with the full demo entity topology from `knowledge/reference/rca-domain-data.md`. The script is idempotent.

### Acceptance Criteria
- [ ] Creates all 4 services: `mysql`, `airflow`, `dbt`, `metabase`
- [ ] Creates all 6 tables with realistic columns
- [ ] Creates the full lineage graph (see `knowledge/reference/rca-domain-data.md`)
- [ ] Creates all 4 DQ test cases
- [ ] Sets `airflow.ingest_orders_daily` pipeline status to `Failed` (last run at 03:00 UTC)
- [ ] Script is idempotent — running it twice does not create duplicates
- [ ] `uv run python scripts/seed_demo.py` completes without errors and prints a summary

---

## DLD-019 — End-to-End Real Agent Smoke Test

**Priority:** P0
**Estimate:** 1 hour
**Depends on:** DLD-011 through DLD-018

### Context
Run `scripts/trigger_demo.py` against the seeded OM data and verify that the real agent produces a HIGH-confidence report identifying the pipeline failure as the root cause.

### Acceptance Criteria
- [ ] `uv run python scripts/trigger_demo.py` sends a valid webhook
- [ ] Within 3 minutes, an incident appears on the dashboard with `status=complete`
- [ ] `root_cause_summary` mentions the pipeline failure (not the stub text)
- [ ] `confidence_label` is `HIGH`
- [ ] At least 3 `timeline_events` are recorded
- [ ] At least 2 `blast_radius_consumers` are recorded
- [ ] Prometheus `/metrics` shows `rca_requests_total{status="success"} 1.0`
- [ ] `make test` passes all Sprint 1 + Sprint 2 tests (target: ≥ 35 tests total)

### Sprint 2 Definition of Done
All 9 tickets ✅, real agent produces HIGH-confidence report on demo data, ≥ 35 tests passing.
