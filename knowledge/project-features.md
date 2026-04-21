# Feature Scope List

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

This is the scope gate for the entire project. Before implementing anything, check this file.

- `[MVP]` — must be built and demo-ready by April 26, 2026
- `[FUTURE]` — explicitly not in scope; do not build without written approval

If a feature is not listed at all, it is out of scope. Ask before adding it.

---

## Webhook and Event Handling

- `[MVP]` POST `/webhook/openmetadata` endpoint accepting OpenMetadata event payloads
- `[MVP]` Payload validation with structured 400 error responses
- `[MVP]` Event type filtering — process `testCaseFailed` only, silently ignore all others
- `[MVP]` Async enqueue to Celery on valid event receipt; return 202 immediately
- `[FUTURE]` Webhook signature verification (HMAC secret)
- `[FUTURE]` Support for additional event types: `testCasePassed`, `pipelineFailed`
- `[FUTURE]` Event deduplication within a rolling time window

---

## RCA Agent

- `[MVP]` Direct OpenAI-compatible tool-calling loop (no framework)
- `[MVP]` Configurable LLM provider via `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
- `[MVP]` Default provider: Gemini via OpenAI-compatible endpoint
- `[MVP]` Structured `RCAReport` JSON output on every run
- `[MVP]` Confidence score with HIGH / MEDIUM / LOW label
- `[MVP]` Maximum iteration guard (15 tool call iterations)
- `[MVP]` Fallback LOW-confidence report on max iteration or LLM error
- `[MVP]` Remediation steps in every report
- `[FUTURE]` Multi-agent setup where a supervisor delegates to specialist sub-agents
- `[FUTURE]` Fine-tuned model for data quality reasoning
- `[FUTURE]` Streaming agent output to dashboard in real-time
- `[FUTURE]` Agent memory across incidents (vector similarity search)

---

## Tool Layer

- `[MVP]` `get_upstream_lineage(table_fqn, depth)` — traverse upstream lineage up to depth 3
- `[MVP]` `get_dq_test_results(table_fqn, last_n)` — fetch last N DQ test results
- `[MVP]` `get_pipeline_entity_status(pipeline_fqn)` — fetch Pipeline entity status
- `[MVP]` `get_entity_owners(entity_fqn, entity_type)` — resolve entity owners
- `[MVP]` `calculate_blast_radius(table_fqn, depth)` — traverse downstream lineage
- `[MVP]` `find_past_incidents(table_fqn, limit)` — search local incident history
- `[FUTURE]` `get_column_lineage(table_fqn, column_name)` — column-level lineage traversal
- `[FUTURE]` `get_schema_change_history(table_fqn)` — fetch OpenMetadata change events for a table
- `[FUTURE]` `run_profiler(table_fqn)` — trigger a data profiler run via OM API
- `[FUTURE]` `query_ml_model_features(model_fqn)` — check if a failing table feeds an ML model

---

## OpenMetadata Integration

- `[MVP]` JWT-authenticated REST client for all OM API calls
- `[MVP]` Lineage API: `GET /api/v1/lineage/table/{id}` (upstream and downstream)
- `[MVP]` Test results API: `GET /api/v1/dataQuality/testCases/testSuites/{fqn}/testCaseResults`
- `[MVP]` Pipeline status API: `GET /api/v1/pipelines/{fqn}/pipelineStatus`
- `[MVP]` Entity owners via Teams and Users API
- `[MVP]` Incident creation via `POST /api/v1/incidents` (or equivalent)
- `[MVP]` Retry with exponential backoff on transient OM API errors
- `[FUTURE]` OpenMetadata MCP server integration
- `[FUTURE]` Support for OpenMetadata Cloud (managed) instances
- `[FUTURE]` Bulk entity resolution for large lineage graphs

---

## Incident Reporting and Notifications

- `[MVP]` Persist every RCA report to PostgreSQL
- `[MVP]` Timeline events linked to incident record
- `[MVP]` Blast radius consumers linked to incident record
- `[MVP]` Slack notification on RCA completion (fire-and-forget)
- `[MVP]` OpenMetadata incident entity creation on RCA completion
- `[MVP]` Notification failures do not abort or fail the RCA task
- `[FUTURE]` Email notification via SMTP
- `[FUTURE]` PagerDuty incident creation
- `[FUTURE]` Microsoft Teams notification
- `[FUTURE]` Incident severity auto-escalation based on blast radius size

---

## Dashboard and Visualization

- `[MVP]` Jinja2-rendered incidents list page at `GET /`
- `[MVP]` Incident detail page at `GET /incidents/{id}`
- `[MVP]` React Flow lineage graph (CDN, no build step) with root cause node highlighted
- `[MVP]` Event timeline in chronological order on detail page
- `[MVP]` Blast radius consumer table on detail page
- `[MVP]` RCA narrative, confidence badge, and remediation steps on detail page
- `[MVP]` Styled 404 page for unknown incident IDs
- `[FUTURE]` User authentication and access control for dashboard
- `[FUTURE]` Incident status management (open / acknowledged / resolved)
- `[FUTURE]` Filtering and search on the incidents list
- `[FUTURE]` Responsive mobile layout
- `[FUTURE]` Real-time dashboard updates via WebSocket or SSE
- `[FUTURE]` Incident export to PDF or Markdown

---

## Observability and Metrics

- `[MVP]` Prometheus metrics endpoint at `GET /metrics`
- `[MVP]` `rca_requests_total` counter labelled by status
- `[MVP]` `rca_duration_seconds` histogram
- `[MVP]` `rca_tool_calls_total` counter labelled by tool name
- `[MVP]` `rca_confidence_score` gauge
- `[MVP]` `blast_radius_size` histogram
- `[MVP]` `rca_errors_total` counter labelled by error type
- `[MVP]` Structured JSON logs for every agent tool call
- `[FUTURE]` Grafana dashboard provisioned automatically via Docker Compose
- `[FUTURE]` OpenTelemetry tracing across agent tool calls
- `[FUTURE]` Alertmanager rules for high error rates

---

## Demo Seeding and Scripts

- `[MVP]` `scripts/seed_demo.py` — idempotent OpenMetadata entity seeder
- `[MVP]` Seeded entities: database service, schema, `raw_orders`, `stg_orders`, `analytics_revenue`, column lineage, pipeline entity, DQ test suite with two test cases
- `[MVP]` `scripts/trigger_demo.py` — marks a DQ test as failed to fire the webhook
- `[MVP]` `make demo` — runs seed + trigger and confirms incident is produced
- `[MVP]` `make dev` — starts the full Docker Compose stack for local development
- `[FUTURE]` Multiple seed scenarios (different failure types, deeper lineage)
- `[FUTURE]` Automated demo video generation
