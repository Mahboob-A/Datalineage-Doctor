# Agent Plan: Sprint 4 Observability + Polish

## Plan Metadata
- Plan ID: agent-plan-sprint-4-1
- Date: 2026-04-25
- Sprint: 4
- Plan Type: Sprint kickoff
- Naming convention: knowledge/plan/agent-plan-[sprint-number-or-core-essence]-[number].md
- Previous plans reviewed:
  - knowledge/plan/agent-plan-sprint-1-1.md
  - knowledge/plan/agent-plan-sprint-2-1.md
  - knowledge/plan/agent-plan-sprint-3-1.md

## Mandatory Pre-Sprint Protocol
Before starting implementation, complete this sequence:
1. Read AGENTS entry file.
2. Read current project status file.
3. Read previous plans in knowledge/plan/.
4. Read current sprint ticket file.
5. Read dependent service docs and architecture docs.
6. Create this plan file first.
7. Begin coding only after the plan is finalized.

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
- knowledge/reference/rca-domain-data.md
- knowledge/rca-agent-architecture.md
- knowledge/services/app.md
- knowledge/services/worker.md
- knowledge/services/agent.md
- knowledge/services/om-client.md
- knowledge/sprint-tickets/sprint-4.md
- knowledge/sprint-progress/sprint-3-progress.md
- knowledge/plan/agent-plan-template.md
- knowledge/plan/agent-plan-sprint-3-1.md

## Current State Snapshot
- Current sprint in status file: Sprint 4 — Observability + Polish.
- Ticket state summary: Sprint 4 kickoff; execution not started yet.
- Completed work carried in: Sprint 3 finalized (DLD-020 to DLD-024 complete with OM incident API compatibility guard documented).
- Blockers carried in: no active blocker; known platform behavior is OM 1.5.4 lacks `/api/v1/incidents` endpoint.
- Main objective now: make demo + observability fully judge-ready with reproducible one-command flow and complete README story.

## Scope
### In Scope
- DLD-025 metrics instrumentation wired to real runtime behavior.
- DLD-026 Prometheus + Grafana provisioning and dashboard panels.
- DLD-027 reliable one-command `make demo` flow from running stack.
- DLD-028 complete hackathon-grade README.
- DLD-029 final integration pass and submission polish gates.

### Out of Scope
- New product features not listed in Sprint 4 tickets.
- Architecture rewrites or stack changes outside locked decisions.
- Any `[FUTURE]` work from project feature backlog.

## Locked Constraints
- Respect module dependency chain: `app -> worker -> agent -> om_client`.
- Keep webhook route queue-only and fast.
- Keep OM API calls isolated in `om_client/`.
- Follow locked stack and coding rules from `ai-rules.md`.
- Keep external notification/OM incident write behavior non-fatal.
- Preserve MVP boundaries and avoid scope creep during polish.

## Execution Plan

### Wave A (Foundational / Blocking)
1. DLD-025 Prometheus Metrics Instrumentation.
2. DLD-026 Grafana Dashboard.

### Wave B (Parallelizable)
1. DLD-027 `make demo` one-command flow.
2. DLD-028 README.

### Wave C (Integration / Gate)
1. DLD-029 Final integration and submission polish.
2. Sprint traceability updates in status/progress docs.

## Ticket-Level Plan Table
| Ticket | Outcome | Dependencies | Acceptance Gate |
|---|---|---|---|
| DLD-025 | All 6 metrics emit real values from live task/tool execution paths | DLD-009 | `/metrics` shows non-zero RCA metrics after one demo run |
| DLD-026 | Prometheus + Grafana services and pre-provisioned dashboard with 6 panels | DLD-025 | Grafana opens preloaded dashboard with populated data post-demo |
| DLD-027 | `make demo` performs wait, seed, trigger, poll, and open-dashboard flow | DLD-018, Sprint 3 complete | Fresh run is reproducible, idempotent, and completes within time target |
| DLD-028 | Full README telling problem-solution-demo-architecture story | DLD-025..027 context | README sections complete with no placeholders |
| DLD-029 | End-to-end quality gate pass for runtime, tests, lint, UX, observability | DLD-025..028 | cold-start flow, test/lint pass, and dashboard/metrics acceptance all satisfied |

## Verification Gates (Definition of Done)
Plan/sprint is complete only if all required checks pass:
1. `make clean && make dev && make migrate && make demo` succeeds on the project stack.
2. `make test` passes (target in ticket: >= 60 tests).
3. `make lint` passes with zero errors.
4. `/metrics` shows real increments/observations for all 6 Sprint 4 metrics after demo run.
5. Grafana dashboard panels show non-zero runtime data after demo run.
6. Dashboard UX remains stable (incident list/detail + React Flow graph load without errors).
7. `README.md` is complete and submission-ready.

## Deliverables
- Runtime metrics wiring and error classification instrumentation.
- Prometheus/Grafana docker + provisioning + dashboard JSON.
- One-command demo flow (`make demo` and wait scripts).
- Submission-ready README with architecture and observability narrative.
- Updated sprint progress and status traceability entries.

## Risk Register
1. Risk: metric instrumentation misses edge paths (failure/retry branches).
   - Impact: high
   - Mitigation: validate both success and simulated failure counters in dedicated tests/log checks.
2. Risk: Grafana provisioning mismatch (datasource/path errors).
   - Impact: medium
   - Mitigation: verify provisioning tree paths in-container and assert dashboard auto-load on startup.
3. Risk: `make demo` timing flakiness on slower machines.
   - Impact: high
   - Mitigation: deterministic wait scripts with explicit timeout, status logs, and retry-safe sequencing.
4. Risk: README quality drift under time pressure.
   - Impact: medium
   - Mitigation: finish README before final gate and validate every ticket acceptance item against section checklist.

## Change Control
If major deviation happens:
1. Record deviation in this file under Deviations.
2. If re-planning is needed, create next numbered plan file.
3. Reference superseded plan and reason.

## Deviations
- None yet.

## Mandatory Traceability Updates After Sprint Completion
1. Update sprint ticket file:
   - File: knowledge/sprint-tickets/sprint-4.md
   - Add section:

### Agent Plan Traceability
- Plan ID: agent-plan-sprint-4-1
- Completion date: YYYY-MM-DD
- Covered tickets: DLD-025 to DLD-029
- Major decisions:
  - Prioritized metrics and observability foundation before demo/README polish.
  - Kept OM incident-create compatibility behavior non-fatal due OM version endpoint availability.
  - Kept demo flow deterministic with wait-and-poll scripts.
- Deviations from plan: <none/details>

2. Update project status file:
   - File: knowledge/agent-sync/ai-project-status.md
   - Add line under Decisions Made This Session:
   - Sprint 4 completed via agent-plan-sprint-4-1.

3. Update sprint progress file:
   - File: knowledge/sprint-progress/sprint-4-progress.md
   - Keep ticket-level progress, blockers, validation outputs, and closure notes current.

## Next Plan Trigger
Before Sprint 5 starts:
1. Re-read AGENTS, status, previous plans, and Sprint 5 ticket file.
2. Create: knowledge/plan/agent-plan-sprint-5-1.md
3. Carry forward unresolved risks, blockers, and verification gaps.
