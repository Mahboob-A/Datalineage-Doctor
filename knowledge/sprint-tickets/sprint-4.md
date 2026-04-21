# Sprint 4 Tickets — Observability + Polish

**Sprint:** 4 of 5
**Goal:** Grafana dashboard wired to Prometheus metrics, one-command `make demo` flow, polished README. Project is submission-ready.
**Dates:** April 23–24, 2026
**Depends on:** Sprint 3 fully complete

---

## DLD-025 — Prometheus Metrics Instrumentation

**Priority:** P0
**Estimate:** 1.5 hours
**Depends on:** DLD-009 (metrics endpoint exists)

### Context
Wire all 6 Prometheus metrics to their actual increment/observe calls throughout the codebase. The `/metrics` endpoint exists but currently shows zero values for everything. After this ticket, running the demo populates real metrics visible in Grafana.

### Metrics and Where to Increment

| Metric | Type | Where |
|---|---|---|
| `rca_requests_total{status}` | Counter | `worker/tasks.py` — after task completes or fails |
| `rca_duration_seconds` | Histogram | `worker/tasks.py` — `time.time()` before/after `_run()` |
| `rca_tool_calls_total{tool_name}` | Counter | `agent/tools/registry.py` — after each `dispatch_tool()` |
| `rca_confidence_score` | Gauge | `worker/tasks.py` — after report persisted |
| `blast_radius_size` | Histogram | `worker/tasks.py` — `len(report.blast_radius_consumers)` |
| `rca_errors_total{error_type}` | Counter | `worker/tasks.py` + `agent/loop.py` — on specific error types |

### Acceptance Criteria
- [ ] All 6 metrics increment/observe with real values after one demo run
- [ ] `rca_requests_total{status="success"}` increments on successful task completion
- [ ] `rca_requests_total{status="failure"}` increments on task failure after all retries
- [ ] `rca_duration_seconds` records actual wall-clock time of the full agent run
- [ ] `rca_tool_calls_total` has a label per tool name — at least 5 distinct tool names after one run
- [ ] `rca_confidence_score` shows the confidence score of the most recent completed run
- [ ] `blast_radius_size` shows the count of downstream consumers
- [ ] `rca_errors_total{error_type="llm_timeout"}` increments when tenacity retries are exhausted
- [ ] `rca_errors_total{error_type="om_api_error"}` increments when OM returns 5xx
- [ ] After one demo run: `curl http://localhost:8000/metrics | grep rca_requests_total` shows `1.0`

---

## DLD-026 — Grafana Dashboard

**Priority:** P0 — strong judging signal
**Estimate:** 2 hours
**Depends on:** DLD-025

### Context
Add Grafana and a pre-built dashboard to the Docker Compose stack. Grafana scrapes Prometheus and shows the 6 key metrics in a single-page dashboard. Judges can open it alongside the web dashboard and see the observability story.

### Acceptance Criteria
- [ ] `grafana` service added to `docker-compose.yml` on port 3000
- [ ] `prometheus` service added to `docker-compose.yml` on port 9090
- [ ] `prometheus.yml` scrapes `app:8000/metrics` every 15 seconds
- [ ] Grafana provisioned automatically via `grafana/provisioning/` — no manual setup required
- [ ] Dashboard JSON file at `grafana/dashboards/datalineage-doctor.json`
- [ ] Dashboard has 6 panels:
  - RCA Requests (counter — rate over time, line chart)
  - RCA Duration (histogram — p50/p95 over time, line chart)
  - Confidence Score (gauge — last value, big number panel)
  - Tool Calls by Tool (bar chart — label breakdown)
  - Blast Radius Size (histogram — p50/p95)
  - Error Rate (counter — rate over time)
- [ ] `make dev` starts Grafana, Prometheus, and all existing services
- [ ] `http://localhost:3000` opens Grafana (admin/admin) with the dashboard pre-loaded
- [ ] After one `make demo` run, all 6 panels show non-zero data

### Grafana Provisioning Files
```
grafana/
├── provisioning/
│   ├── datasources/
│   │   └── prometheus.yml    # Configures Prometheus as the default datasource
│   └── dashboards/
│       └── dashboard.yml     # Points Grafana to the dashboard JSON file
└── dashboards/
    └── datalineage-doctor.json  # The pre-built dashboard definition
```

---

## DLD-027 — make demo One-Command Flow

**Priority:** P0 — judges run this
**Estimate:** 1 hour
**Depends on:** DLD-018 (seed script), Sprint 3 complete

### Context
`make demo` must be a single command that seeds OpenMetadata, waits for it to be ready, triggers a DQ failure, and opens the dashboard. It must work on a fresh `make clean && make dev` without any manual steps. This is the first command a judge runs.

### Acceptance Criteria
- [ ] `make demo` runs `seed_demo.py` (waits for OM to be healthy first)
- [ ] `make demo` runs `trigger_demo.py` after seeding completes
- [ ] `make demo` prints a status message every 15 seconds while waiting for the incident to complete
- [ ] `make demo` prints a final "✅ Incident complete — view at http://localhost:8000" message
- [ ] `make demo` opens `http://localhost:8000` in the default browser (using `open` on Mac, `xdg-open` on Linux)
- [ ] The entire flow completes within 3 minutes on a machine with the stack already running
- [ ] `make demo` is idempotent — running it twice creates a second incident without errors

### Updated Makefile Target
```makefile
demo:
	@echo "⏳ Waiting for OpenMetadata to be ready..."
	@docker compose exec app uv run python scripts/wait_for_om.py
	@echo "🌱 Seeding demo data..."
	@docker compose exec app uv run python scripts/seed_demo.py
	@echo "💥 Triggering DQ failure..."
	@docker compose exec app uv run python scripts/trigger_demo.py
	@echo "⏳ Waiting for RCA to complete..."
	@docker compose exec app uv run python scripts/wait_for_incident.py
	@echo "✅ Done! Opening dashboard..."
	@open http://localhost:8000 || xdg-open http://localhost:8000 || true
```

### New Script: `scripts/wait_for_om.py`
Polls `http://openmetadata_server:8585/api/v1/system/status` until HTTP 200, with a 5-minute timeout.

### New Script: `scripts/wait_for_incident.py`
Polls `http://app:8000/api/incidents/latest` every 10 seconds until `status=complete`, with a 3-minute timeout.

---

## DLD-028 — README

**Priority:** P0 — judges read this first
**Estimate:** 2 hours
**Depends on:** All previous sprints complete

### Context
Write the project README. This is the first thing judges read. It must tell the story compellingly, show what the project does, explain how to run it, and highlight the technical depth. It is also the hackathon submission document.

### Acceptance Criteria
- [ ] `README.md` at project root (replaces the placeholder from DLD-001)
- [ ] Includes a one-paragraph elevator pitch (problem → solution → impact)
- [ ] Includes a demo GIF or screenshot of the dashboard (incident detail page with lineage graph)
- [ ] Includes the 9 AM crisis demo story (see `knowledge/a_master_prompt.md` or `knowledge/c_hackathon_ideas.md`)
- [ ] Clear "Quick Start" section: prerequisites, `git clone`, `make dev`, `make demo`, open browser
- [ ] Architecture diagram (ASCII or Mermaid) showing the 5 components
- [ ] Features section listing all implemented features
- [ ] Observability section explaining the 6 Prometheus metrics and Grafana dashboard
- [ ] "How It Works" section explaining the 5-step RCA agent loop
- [ ] Tech stack table
- [ ] Hackathon tracks targeted: T-01 (MCP-adjacent AI), T-02 (Observability), T-06 (Governance)
- [ ] OpenMetadata APIs used (lineage, DQ, pipeline, incident)
- [ ] Known limitations / future work section

### README Structure
```markdown
# DataLineage Doctor 🩺

> *"Your Revenue dashboard shows $0. It's 9 AM. The CEO is asking questions."*

## What It Does
## Demo
## Quick Start
## Architecture
## How the RCA Agent Works
## Features
## Observability
## Tech Stack
## OpenMetadata Integration
## Hackathon Tracks
## Future Work
```

---

## DLD-029 — Final Integration + Submission Polish

**Priority:** P0
**Estimate:** 2 hours
**Depends on:** DLD-025 through DLD-028

### Context
Final quality pass before demo recording. Fix any rough edges found during end-to-end testing.

### Acceptance Criteria
- [ ] `make clean && make dev && make migrate && make demo` works on a fresh clone — tested
- [ ] `make test` passes all tests (target: ≥ 60 tests, ≥ 80% coverage)
- [ ] `make lint` passes with zero errors
- [ ] No `print()` statements in source code (only in scripts)
- [ ] No hardcoded strings for statuses or entity types outside enums
- [ ] All 6 Prometheus metrics show non-zero values after one demo run
- [ ] Grafana dashboard shows data after one demo run
- [ ] Dashboard loads in under 2 seconds on localhost
- [ ] React Flow graph renders without console errors
- [ ] README is complete and has no placeholder sections

### Sprint 4 Definition of Done
All 5 tickets ✅, full demo flow reproducible from cold start in under 5 minutes, ≥ 60 tests, README complete, Grafana shows data.
