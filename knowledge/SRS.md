# Software Requirements Specification

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Document Scope

This document defines the full functional and non-functional requirements for DataLineage Doctor. Every requirement has a unique code. Sprint tickets reference these codes in their `Why:` field. Tests reference them in their docstrings. This traceability thread connects planning, implementation, and verification.

**Requirement code format:**
- Functional: `FR-[AREA]-[NN]` — e.g., `FR-WEBHOOK-01`
- Non-functional: `NFR-[AREA]-[NN]` — e.g., `NFR-PERF-01`

---

## Functional Requirements

### FR-WEBHOOK — Webhook Receiver

---

**FR-WEBHOOK-01**
**Description:** The system must expose a `POST /webhook/openmetadata` endpoint that accepts OpenMetadata event payloads.
**Acceptance criteria:**
- Endpoint exists and accepts `application/json` POST requests
- Endpoint returns `202 Accepted` for valid `testCaseFailed` payloads

---

**FR-WEBHOOK-02**
**Description:** The endpoint must validate the incoming payload for required fields before enqueuing.
**Acceptance criteria:**
- Payloads missing `eventType`, `entityType`, or `entity` fields return `400 Bad Request`
- A structured JSON error body is returned on validation failure

---

**FR-WEBHOOK-03**
**Description:** The system must filter incoming events and only process `testCaseFailed` event types.
**Acceptance criteria:**
- Events with `eventType != "testCaseFailed"` return `202 Accepted` with body `{"status": "ignored"}`
- No Celery task is enqueued for non-`testCaseFailed` events

---

**FR-WEBHOOK-04**
**Description:** On receipt of a valid `testCaseFailed` event, the system must enqueue an RCA task to the Celery task queue and return immediately.
**Acceptance criteria:**
- The `202 Accepted` response is returned before the agent begins processing
- A Celery task ID is logged

---

**FR-WEBHOOK-05**
**Description:** The endpoint must handle deserialization errors gracefully.
**Acceptance criteria:**
- Non-JSON request bodies return `400 Bad Request` with a descriptive error message
- The server does not return a `500` error for malformed payloads

---

### FR-AGENT — RCA Agent

---

**FR-AGENT-01**
**Description:** The system must use an OpenAI-compatible LLM to reason over OpenMetadata entities and produce a root cause analysis.
**Acceptance criteria:**
- The agent successfully calls at least two tools before producing its final report
- The final report is a valid `RCAReport` object (see `knowledge/reference/rca-domain-data.md`)

---

**FR-AGENT-02**
**Description:** The LLM provider, model, and API key must be fully configurable via environment variables with no hardcoded values.
**Acceptance criteria:**
- Changing `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` env vars switches the provider with no code changes
- Default example configuration uses Gemini via its OpenAI-compatible endpoint

---

**FR-AGENT-03**
**Description:** The agent must use a direct tool-calling loop implemented with the `openai` Python SDK. No agent framework (LangChain, LangGraph, etc.) may be used.
**Acceptance criteria:**
- `openai` is the only LLM SDK in `pyproject.toml`
- The loop is implemented as an explicit `while` loop that processes tool call responses

---

**FR-AGENT-04**
**Description:** The agent loop must terminate cleanly under two conditions: the model returns `finish_reason == "stop"` with a final answer, or the loop reaches the maximum iteration limit.
**Acceptance criteria:**
- Loop terminates and produces a report on `finish_reason == "stop"`
- Loop terminates and produces a fallback LOW-confidence report after 15 iterations

---

**FR-AGENT-05**
**Description:** The agent must assign a confidence score to its root cause conclusion.
**Acceptance criteria:**
- The `confidence_score` field is a float between 0.0 and 1.0
- The `confidence_label` is correctly derived as HIGH (≥ 0.85), MEDIUM (0.60–0.84), or LOW (< 0.60)

---

**FR-AGENT-06**
**Description:** The agent must produce at least one actionable remediation step in its final report.
**Acceptance criteria:**
- The `remediation_steps` field is a non-empty list of strings
- Each step is a plain-language action, not a technical error trace

---

### FR-TOOLS — Tool Layer

Each tool is a Python function registered in the tool registry. All tools call the OpenMetadata REST API via `om_client`.

---

**FR-TOOLS-01**
**Tool:** `get_upstream_lineage`
**Description:** Traverses the upstream lineage graph from a given table FQN up to a configurable depth (default 3).
**Acceptance criteria:**
- Returns a list of upstream node objects, each with `fqn`, `entity_type`, `service`, and `level`
- Returns an empty list (not an error) when no upstream lineage exists

---

**FR-TOOLS-02**
**Tool:** `get_dq_test_results`
**Description:** Fetches the last N DQ test results for a given table FQN.
**Acceptance criteria:**
- Returns a list of test result objects with `test_name`, `status`, `timestamp`, and `sample_data`
- `n` defaults to 10 if not specified

---

**FR-TOOLS-03**
**Tool:** `get_pipeline_entity_status`
**Description:** Fetches the status of a Pipeline entity from OpenMetadata by its FQN.
**Acceptance criteria:**
- Returns `pipeline_status`, `last_run_at`, and `task_statuses` for the given pipeline
- Returns a structured "not found" response (not an exception) when the pipeline FQN does not exist

---

**FR-TOOLS-04**
**Tool:** `get_entity_owners`
**Description:** Resolves the owners of any OpenMetadata entity (table, pipeline, dashboard) by FQN and entity type.
**Acceptance criteria:**
- Returns a list of owner objects with `name`, `type` (user or team), and `email` where available
- Returns an empty list (not an error) when no owners are configured

---

**FR-TOOLS-05**
**Tool:** `calculate_blast_radius`
**Description:** Traverses downstream lineage from a given table FQN up to configurable depth (default 3) and returns all affected consumers.
**Acceptance criteria:**
- Returns a list of downstream consumer objects with `fqn`, `entity_type`, and `level`
- Deduplicates nodes that appear at multiple downstream levels

---

**FR-TOOLS-06**
**Tool:** `find_past_incidents`
**Description:** Searches the local PostgreSQL store for past RCA incidents involving a given table FQN.
**Acceptance criteria:**
- Returns the last N incidents (default 5) for the given table FQN
- Returns an empty list (not an error) when no past incidents exist

---

### FR-REPORT — Incident Reporting

---

**FR-REPORT-01**
**Description:** Every completed RCA run must produce a report persisted to PostgreSQL.
**Acceptance criteria:**
- A row is inserted into the `incidents` table for every completed RCA task
- The report is readable via `GET /incidents/{id}` immediately after the Celery task completes

---

**FR-REPORT-02**
**Description:** The RCA report must include a chronological timeline of events linking pipeline runs, DQ test failures, and upstream changes.
**Acceptance criteria:**
- The `timeline_events` associated with the incident contain at least one entry
- Each entry has `occurred_at`, `event_type`, `entity_fqn`, and `description`

---

**FR-REPORT-03**
**Description:** The report must include a structured blast radius section listing all downstream consumers identified.
**Acceptance criteria:**
- `blast_radius_consumers` are persisted and linked to the incident
- Each consumer has `fqn`, `entity_type`, and `level`

---

**FR-REPORT-04**
**Description:** The report must include the full evidence chain that led to the confidence score.
**Acceptance criteria:**
- The `evidence_chain` field is a non-empty list of strings describing each reasoning step
- The evidence chain is visible in the incident detail dashboard view

---

### FR-NOTIFY — Notifications

---

**FR-NOTIFY-01**
**Description:** On RCA completion, the system must post a formatted summary to the configured Slack webhook URL.
**Acceptance criteria:**
- A Slack message is posted within 30 seconds of RCA task completion
- The message includes: affected table FQN, root cause summary, confidence label, blast radius count

---

**FR-NOTIFY-02**
**Description:** On RCA completion, the system must create an Incident entity in OpenMetadata.
**Acceptance criteria:**
- An incident is created via `POST /api/v1/incidents` (or equivalent OM API endpoint)
- The incident is linked to the failing test entity

---

**FR-NOTIFY-03**
**Description:** Notification failures (Slack or OM incident creation) must not cause the Celery task to fail or the report to be lost.
**Acceptance criteria:**
- If the Slack call fails, the RCA report is still persisted and the task is marked complete
- Notification errors are logged as warnings, not exceptions that abort the task

---

### FR-DASH — Dashboard

---

**FR-DASH-01**
**Description:** The system must serve a Jinja2-rendered incidents list page at `GET /`.
**Acceptance criteria:**
- The page displays a paginated list of incidents ordered by `triggered_at` descending
- Each row shows: table FQN, triggered at, confidence label badge, blast radius count, status

---

**FR-DASH-02**
**Description:** The system must serve an incident detail page at `GET /incidents/{id}`.
**Acceptance criteria:**
- The page renders for a valid incident ID
- The page returns a styled 404 for an unknown ID

---

**FR-DASH-03**
**Description:** The incident detail page must render a React Flow lineage graph (loaded via CDN) showing the affected pipeline with the root cause node highlighted.
**Acceptance criteria:**
- The lineage graph renders in a browser without a build step
- The root cause node is visually distinct (red border or fill)
- Upstream and downstream nodes are included in the graph

---

**FR-DASH-04**
**Description:** The incident detail page must display the event timeline.
**Acceptance criteria:**
- Events are displayed in chronological order with timestamps
- Each event shows its type and entity FQN

---

**FR-DASH-05**
**Description:** The incident detail page must display the blast radius consumer table.
**Acceptance criteria:**
- All downstream consumers are listed with entity type and FQN
- The count of affected consumers is shown prominently

---

**FR-DASH-06**
**Description:** The incident detail page must display the RCA narrative, confidence score, and remediation steps.
**Acceptance criteria:**
- The root cause summary is displayed as a readable paragraph
- The confidence label is displayed as a coloured badge (HIGH=green, MEDIUM=amber, LOW=red)
- Remediation steps are displayed as an ordered list

---

### FR-SEED — Demo Seeding

---

**FR-SEED-01**
**Description:** A seed script at `scripts/seed_demo.py` must create a reproducible demo pipeline in OpenMetadata.
**Acceptance criteria:**
- Running the script against a fresh OpenMetadata instance creates all required entities
- The script is idempotent — running it twice does not create duplicate entities

---

**FR-SEED-02**
**Description:** The seeded demo pipeline must include: a database service, schema, three tables (`raw_orders`, `stg_orders`, `analytics_revenue`), column-level lineage between them, a pipeline entity, and a DQ test suite with at least two test cases.
**Acceptance criteria:**
- All entities are visible in the OpenMetadata UI after seeding
- Lineage graph shows the full `raw → stg → analytics` chain

---

**FR-SEED-03**
**Description:** A trigger script at `scripts/trigger_demo.py` must mark a DQ test as failed to fire a `testCaseFailed` webhook event.
**Acceptance criteria:**
- Running the trigger script results in a webhook event reaching `POST /webhook/openmetadata`
- An RCA task is enqueued and an incident is produced

---

**FR-SEED-04**
**Description:** `make demo` must execute seed, wait, trigger, and open the dashboard in one command.
**Acceptance criteria:**
- Running `make demo` from cold start produces a visible incident in the dashboard within 5 minutes
- No manual steps are required beyond setting `.env` values

---

### FR-METRICS — Observability

---

**FR-METRICS-01**
**Description:** The system must expose Prometheus-compatible metrics at `GET /metrics`.
**Acceptance criteria:**
- The endpoint returns valid Prometheus text format
- The endpoint is reachable without authentication

---

**FR-METRICS-02**
**Description:** The following metrics must be instrumented:

| Metric | Type | Description |
|---|---|---|
| `rca_requests_total` | Counter | Total RCA tasks received, labelled by `status` (success/failure) |
| `rca_duration_seconds` | Histogram | End-to-end agent duration per RCA run |
| `rca_tool_calls_total` | Counter | Total tool calls, labelled by `tool_name` |
| `rca_confidence_score` | Gauge | Confidence score of the most recent RCA run |
| `blast_radius_size` | Histogram | Number of downstream consumers per incident |
| `rca_errors_total` | Counter | Total errors, labelled by `error_type` |

**Acceptance criteria:**
- All six metrics are present in the `/metrics` output after at least one RCA run
- Labels are correctly applied

---

## Non-Functional Requirements

---

**NFR-PERF-01**
**Description:** The webhook endpoint must return a response within 200ms regardless of agent processing time.
**Acceptance criteria:**
- Load test or manual timing confirms P99 response time ≤ 200ms under single-request load

---

**NFR-PERF-02**
**Description:** The full RCA agent loop must complete within 120 seconds for a demo pipeline with up to 3 levels of upstream lineage.
**Acceptance criteria:**
- Timed demo run confirms end-to-end completion within 120 seconds

---

**NFR-RELY-01**
**Description:** Failed Celery tasks must be retried automatically up to 3 times using exponential backoff before being marked as failed.
**Acceptance criteria:**
- Task retry configuration is set in the Celery task decorator
- Retries are observable in Celery logs

---

**NFR-RELY-02**
**Description:** All OpenMetadata API calls must handle transient errors with retry logic (max 3 attempts, exponential backoff starting at 1 second).
**Acceptance criteria:**
- `om_client` methods retry on HTTP 429, 502, 503, and 504 responses
- Persistent failures raise a typed exception after 3 attempts

---

**NFR-TEST-01**
**Description:** The test suite must contain at least 50 passing tests at submission.
**Acceptance criteria:**
- `uv run pytest` exits with code 0 and reports ≥ 50 passed tests

---

**NFR-TEST-02**
**Description:** All external API calls (OpenMetadata, LLM, Slack) must be mocked in tests. No live API calls in the test suite.
**Acceptance criteria:**
- `pytest` passes with no network access required
- External calls are mocked via `pytest-mock` or `respx`

---

**NFR-OBS-01**
**Description:** Every agent tool call must be logged with tool name, input arguments, result summary, and duration.
**Acceptance criteria:**
- Structured log entries exist for every tool call when running in demo mode
- Logs are machine-readable JSON format

---

**NFR-SEC-01**
**Description:** No secrets, API keys, or credentials may appear in source code or committed files.
**Acceptance criteria:**
- `git grep -i "api_key\|password\|secret"` finds no hardcoded values in `.py` files
- All credentials are read via `config.py` from environment variables

---

**NFR-SEC-02**
**Description:** The `.env.example` file must include every required environment variable with placeholder values and inline comments explaining each variable.
**Acceptance criteria:**
- Every variable read by `config.py` appears in `.env.example`
- No real credentials appear in `.env.example`

---

## User Stories

**US-01**
As a data engineer on call, I want to receive a Slack message with the root cause and blast radius within minutes of a DQ failure, so I know exactly what broke and who is affected before I open a single tool.

**US-02**
As a data team lead, I want to open a dashboard and see the full history of data incidents, so I can identify which pipelines fail repeatedly and prioritise remediation work.

**US-03**
As an incident responder, I want to see a lineage graph in the incident detail view with the broken node highlighted, so I can understand the failure in the context of the full pipeline at a glance.

**US-04**
As a data engineer evaluating the tool, I want to run `make demo` from scratch and see a complete incident produced end-to-end, so I can verify the system works before using it on a real pipeline.

**US-05**
As a platform operator, I want to see Prometheus metrics for RCA duration and confidence scores, so I can monitor agent performance over time.

---

## Requirement Traceability Summary

| Area | Codes | Count |
|---|---|---|
| Webhook | FR-WEBHOOK-01 to FR-WEBHOOK-05 | 5 |
| Agent | FR-AGENT-01 to FR-AGENT-06 | 6 |
| Tools | FR-TOOLS-01 to FR-TOOLS-06 | 6 |
| Report | FR-REPORT-01 to FR-REPORT-04 | 4 |
| Notifications | FR-NOTIFY-01 to FR-NOTIFY-03 | 3 |
| Dashboard | FR-DASH-01 to FR-DASH-06 | 6 |
| Seed | FR-SEED-01 to FR-SEED-04 | 4 |
| Metrics | FR-METRICS-01 to FR-METRICS-02 | 2 |
| Performance | NFR-PERF-01 to NFR-PERF-02 | 2 |
| Reliability | NFR-RELY-01 to NFR-RELY-02 | 2 |
| Testing | NFR-TEST-01 to NFR-TEST-02 | 2 |
| Observability | NFR-OBS-01 | 1 |
| Security | NFR-SEC-01 to NFR-SEC-02 | 2 |
| **Total** | | **45** |
