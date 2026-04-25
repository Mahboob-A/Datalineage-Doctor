# Sprint 3 Tickets — Dashboard + Notifications

**Sprint:** 3 of 5
**Goal:** Polished incident detail page with React Flow lineage graph, Slack notifications, and OM incident creation. The dashboard is demo-ready.
**Dates:** April 21–22, 2026
**Depends on:** Sprint 2 fully complete

---

## DLD-020 — Incident Detail Page

**Priority:** P0
**Estimate:** 3 hours
**Depends on:** DLD-008 (list page), DLD-019 (real incidents in DB)

### Context
Build `GET /incidents/{id}` — the most important page in the dashboard. Judges will spend most of their time here. It must show the root cause, confidence badge, evidence chain, remediation steps, timeline, blast radius table, and the React Flow lineage graph. See `knowledge/reference/api-spec.md` for the full page content specification.

### Acceptance Criteria
- [x] `app/routers/dashboard.py` has `GET /incidents/{id}` rendering `incident_detail.html`
- [x] Page shows: summary header, root cause narrative, confidence score + badge, evidence chain, remediation steps
- [x] Timeline section shows `timeline_events` ordered by `sequence` ascending
- [x] Blast radius table shows `blast_radius_consumers` grouped by level
- [x] React Flow graph loaded from CDN (`https://cdn.jsdelivr.net/npm/reactflow`)
- [x] Lineage graph data injected as JSON in a `<script id="graph-data" type="application/json">` tag
- [x] Root cause node renders with red border (use `is_root_cause: true` on the node)
- [x] Healthy upstream nodes render in default colour; downstream nodes in amber
- [x] 404 returned when incident ID does not exist
- [x] Page is responsive

### Graph Data Builder
Create `app/services/graph_builder.py` that converts incident + blast_radius_consumers + timeline_events into the React Flow `{nodes, edges}` shape defined in `knowledge/reference/api-spec.md`.

### Template Files to Create
```
dashboard/templates/
├── base.html                  # Already exists from DLD-008
├── incidents_list.html        # Already exists from DLD-008
└── incident_detail.html       # New in this ticket
```

---

## DLD-021 — Slack Notification

**Priority:** P0
**Estimate:** 1.5 hours
**Depends on:** DLD-019 (real RCAReport)

### Context
Build `agent/notifications.py` with `notify_slack()`. Sends a Slack Block Kit message when an incident completes. See `knowledge/services/agent.md` for the fire-and-forget pattern.

### Acceptance Criteria
- [x] `notify_slack(report, table_fqn)` sends a Block Kit message to `SLACK_WEBHOOK_URL`
- [x] Message includes: table FQN, confidence badge (HIGH/MEDIUM/LOW with emoji), root cause summary (truncated to 200 chars), blast radius count, link to incident detail page
- [x] If `SLACK_ENABLED=false` or `SLACK_WEBHOOK_URL` is empty, the call is skipped silently
- [x] HTTP errors are caught, logged as warning, function returns `False`
- [x] `worker/tasks.py` calls `notify_slack()` after `save_incident()` completes
- [x] `incident.slack_notified` is set to `True` on success
- [x] Tests: `SLACK_ENABLED=false` skips call, successful mock HTTP POST sets `slack_notified=True`

### Slack Block Kit Message Shape
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "🔴 RCA Complete — HIGH Confidence"}
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Table:*
`mysql.default.raw_orders`"},
        {"type": "mrkdwn", "text": "*Blast Radius:*
4 downstream consumers affected"}
      ]
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*Root Cause:*
Pipeline ingest_orders_daily failed at 03:00 UTC..."}
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "View Incident"},
          "url": "http://localhost:8000/incidents/{incident_id}"
        }
      ]
    }
  ]
}
```

---

## DLD-022 — OpenMetadata Incident Creation

**Priority:** P1
**Estimate:** 1.5 hours
**Depends on:** DLD-019, DLD-006

### Context
After an RCA completes, create a corresponding incident entity in OpenMetadata itself. This closes the loop — the analysis done in DataLineage Doctor is reflected back in the metadata platform. See `knowledge/services/om-client.md` for the OMClient pattern.

### Acceptance Criteria
- [x] `om_client/incidents.py` has `create_incident(table_fqn, report)` that POSTs to OM
- [x] `agent/notifications.py` extended with `create_om_incident()`
- [x] `worker/tasks.py` calls `create_om_incident()` after `notify_slack()`
- [x] `incident.om_incident_id` is set on the local incident row after successful creation
- [x] OM API errors are caught and logged as warnings — they do not fail the task
- [x] Tests: successful creation (sets `om_incident_id`), OM API error (logs warning, does not raise)

### OM API Call
```
POST /api/v1/incidents
{
  "name": "dld-{incident_id}",
  "entityReference": {"type": "table", "fqn": "{table_fqn}"},
  "incidentType": "dataQuality",
  "description": "{root_cause_summary}",
  "severity": "Severity2"  // HIGH=Severity2, MEDIUM=Severity3, LOW=Severity4
}
```

---

## DLD-023 — Dashboard Polish Pass

**Priority:** P1
**Estimate:** 2 hours
**Depends on:** DLD-020

### Context
The dashboard needs to look sharp for the demo video. This ticket covers visual polish, loading states, error pages, and the empty state on the list page.

### Acceptance Criteria
- [x] `base.html` has a clean header with the DataLineage Doctor logo (SVG inline), nav links (Dashboard, GitHub), dark/light mode toggle
- [x] Incidents list page: status badges are colour-coded pills, confidence badges are coloured, table rows have subtle hover state
- [x] Incident detail page: confidence score shown as a large number with a colour ring (HIGH=green, MEDIUM=amber, LOW=red)
- [x] Timeline renders as a vertical timeline component (not a plain list)
- [x] Blast radius table has entity type icons (table, dashboard, ML model)
- [x] 404 page exists and is styled (not a raw FastAPI error)
- [x] 500 page exists and is styled
- [x] Processing incidents show a spinner/animation on both list and detail pages
- [x] All pages pass basic accessibility checks (alt text, semantic HTML, tab navigation)

### Design Tokens
Use the Nexus design system CSS variables defined in `knowledge/development-guideline.md`. Do not use inline styles or arbitrary colour values.

---

## DLD-024 — Sprint 3 Integration Test

**Priority:** P0
**Estimate:** 30 minutes
**Depends on:** DLD-020 through DLD-023

### Context
Full end-to-end flow with Slack notification and OM incident creation. The demo story works from start to finish.

### Acceptance Criteria
- [x] `make demo` equivalent seed+trigger flow produces a complete incident visible on the dashboard (validated via `scripts/seed_demo.py` + `scripts/trigger_demo.py`)
- [x] Slack message received in the test workspace (when `SLACK_ENABLED=true` and webhook configured)
- [x] OM incident creation path is implemented and validated as non-fatal with compatibility guard on OM `1.5.4` (endpoint unavailable on this version)
- [x] `incident.om_incident_id` is set when OM incidents API is available; remains `null` by design on OM `1.5.4` where `/api/v1/incidents` is not exposed
- [x] Incident detail page shows React Flow graph with at least 4 nodes
- [x] `make test` passes all Sprint 1 + 2 + 3 tests (target: ≥ 50 tests total)
- [x] Dashboard looks production-quality in a browser at 1280px and 375px

### Sprint 3 Definition of Done
All 5 tickets ✅, full demo flow works end-to-end, ≥ 50 tests passing, dashboard is demo-ready. OM incident persistence is version-dependent and gracefully skipped on OM `1.5.4`.

---

## Agent Plan Traceability

- **Plan ID:** agent-plan-sprint-3-1
- **Completion date:** 2026-04-25 (finalized)
- **Covered tickets:** DLD-020 to DLD-024
- **Major decisions:**
  - Enforced Sprint 2 closure gate before Sprint 3 coding.
  - Kept notification failures non-fatal in worker completion path.
  - Isolated React Flow payload generation in a dedicated graph builder service.
  - Added OM incidents API compatibility check and explicit `om_incidents_api_not_supported` log for OM versions without `/api/v1/incidents`.
- **Deviations from plan:**
  - OM incident ID persistence is environment/version dependent; on OM `1.5.4`, incident endpoint is not available and create is skipped by design.
