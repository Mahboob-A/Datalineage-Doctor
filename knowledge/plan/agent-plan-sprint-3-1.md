# Agent Plan: Sprint 3 Dashboard + Notifications

## Plan Metadata
- Plan ID: agent-plan-sprint-3-1
- Sprint: 3
- Plan Type: Sprint kickoff
- Naming convention: knowledge/plan/agent-plan-[sprint-number-or-core-essence]-[number].md
- Previous plans reviewed:
  - knowledge/plan/agent-plan-sprint-1-1.md
  - knowledge/plan/agent-plan-sprint-2-1.md

## Mandatory Pre-Sprint Protocol (applies to every sprint)
Before starting any sprint, the agent must do this in order:
1. Read AGENTS entry file.
2. Read current project status.
3. Read previous plan files from knowledge/plan/.
4. Read current sprint ticket file and dependent service docs.
5. Create a new sprint plan file using the naming convention.
6. Start implementation only after the plan is created.

## Docs Reviewed For This Plan
- AGENTS.md
- knowledge/agent-sync/ai-project-status.md
- knowledge/agent-sync/ai-rules.md
- knowledge/BRD.md
- knowledge/SRS.md
- knowledge/project-features.md
- knowledge/how-services-connect.md
- knowledge/architecture/data-model.md
- knowledge/reference/api-spec.md
- knowledge/rca-agent-architecture.md
- knowledge/services/app.md
- knowledge/services/worker.md
- knowledge/services/agent.md
- knowledge/services/om-client.md
- knowledge/sprint-progress/sprint-1-progress.md
- knowledge/sprint-progress/sprint-2-progress.md
- knowledge/sprint-tickets/sprint-3.md
- knowledge/plan/agent-plan-template.md
- knowledge/plan/agent-plan-sprint-1-1.md
- knowledge/plan/agent-plan-sprint-2-1.md

## Current State Snapshot
- Current sprint in status file: Sprint 2 (still marked in progress).
- Sprint 1 status: complete.
- Sprint 2 progress file shows planning/setup and active implementation wave.
- Main goal now: execute Sprint 3 deliverables for demo-ready dashboard detail + notifications while preserving locked architecture and scope.

## Sprint 3 Goal
Deliver a polished incident detail experience and complete post-RCA notification loop:
- Incident detail page with React Flow lineage graph and complete RCA sections.
- Slack notification after RCA completion.
- OpenMetadata incident creation after RCA completion.
- Dashboard polish for demo-grade UX and error states.
- End-to-end integration path validated.

## Locked Constraints
- Respect module dependency chain: app -> worker -> agent -> om_client.
- Keep webhook route queue-only and fast.
- Keep Slack/OM notification failures non-fatal (warning-level handling only).
- Keep OM API interactions only inside `om_client/`.
- Use established design tokens/patterns for dashboard styling.
- Keep MVP scope boundaries from `project-features.md` and `SRS.md`.

## Execution Plan (Ticket Order)

### Wave A (blocking foundation)
1. Sprint 2 closure gate (DoD + traceability complete before Sprint 3 coding).
2. DLD-020 Incident Detail Page (`GET /incidents/{id}`, detail template, graph builder).

### Wave B (parallelizable after Wave A)
1. DLD-021 Slack Notification.
2. DLD-022 OpenMetadata Incident Creation.
3. DLD-023 Dashboard Polish Pass.

### Wave C (integration and demo gate)
1. DLD-024 Sprint 3 Integration Test.
2. Sprint traceability and status/progress updates.

## Ticket-Level Plan Table
| Ticket | Outcome | Dependencies | Acceptance Gate |
|---|---|---|---|
| DLD-020 | Incident detail route + template + graph data service + 404 handling | DLD-008, DLD-019 | Detail page renders RCA content, timeline order, grouped blast radius, and valid React Flow payload |
| DLD-021 | Slack Block Kit notify flow in `agent/notifications.py` and task wiring | DLD-019 | Disabled mode skips cleanly, success marks `slack_notified`, HTTP failures logged and non-fatal |
| DLD-022 | OM incident creation API client + task wiring + severity mapping | DLD-019, DLD-006 | Success stores `om_incident_id`; OM errors are warning-level and non-fatal |
| DLD-023 | Dashboard visual/UX polish and styled error pages | DLD-020 | List/detail/error pages meet sprint criteria and token-based styling rules |
| DLD-024 | End-to-end validation of Sprint 3 flow | DLD-020..DLD-023 | Demo flow yields complete incident with detail graph and expected Slack/OM integration behavior |

## Verification Gates
Sprint 3 is complete only if all pass:
1. Existing lint command passes.
2. Existing full test suite command passes with Sprint 3 tests included.
3. Demo flow produces a complete incident visible on dashboard detail page.
4. Incident detail page shows React Flow graph with expected root-cause highlighting.
5. Slack integration behavior matches enabled/disabled/success/failure paths.
6. OM incident creation behavior matches success/failure paths with non-fatal handling.

## Deliverables By End Of Sprint 3
- `GET /incidents/{id}` detail route and `incident_detail.html`.
- `app/services/graph_builder.py` producing API-spec-compliant React Flow nodes/edges.
- Slack notification implementation and worker integration.
- OpenMetadata incident creation implementation and worker integration.
- Dashboard polish deliverables including styled 404/500 and improved visual states.
- Sprint 3 progress/status/traceability updates in knowledge docs.

## Risk Controls
1. Sprint boundary drift (starting Sprint 3 before Sprint 2 closure).
   - Mitigation: explicit closure gate in Wave A before any Sprint 3 implementation.
2. External notification reliability (Slack/OM API failures).
   - Mitigation: warning-level non-fatal handling and explicit test coverage.
3. React Flow integration mismatch.
   - Mitigation: isolate graph transform into service with strict output-shape tests.
4. UI scope creep.
   - Mitigation: implement exactly the DLD-023 acceptance checklist and avoid out-of-scope redesign.

## Post-Sprint Traceability Update (mandatory)
After Sprint 3 completes:
1. Update `knowledge/sprint-tickets/sprint-3.md` with section:

### Agent Plan Traceability
- Plan ID: agent-plan-sprint-3-1
- Completion date: YYYY-MM-DD
- Covered tickets: DLD-020 to DLD-024
- Major decisions:
  - Enforced Sprint 2 closure gate before Sprint 3 coding.
  - Kept notification failures non-fatal in worker completion path.
  - Isolated React Flow payload generation in a dedicated graph builder service.
- Deviations from plan: <none or details>

2. Update `knowledge/agent-sync/ai-project-status.md` under Decisions Made This Session:
- Sprint 3 completed via agent-plan-sprint-3-1.

3. Update sprint progress file for current sprint with completed/in-progress/blocked details.

## Next Plan Trigger
Before Sprint 4 starts, create next plan:
- `knowledge/plan/agent-plan-sprint-4-1.md`
- It must review this file, latest status, Sprint 4 ticket file, and any new docs/decisions.
