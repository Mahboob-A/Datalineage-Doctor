# Agent Plan: Sprint 1 Foundation

## Plan Metadata
- Plan ID: agent-plan-sprint-1-1
- Date: April 20, 2026
- Sprint: 1
- Plan Type: Sprint kickoff
- Naming convention: knowledge/plan/agent-plan-[sprint-number-or-core-essence]-[number].md
- Previous plans reviewed: none

## Mandatory Pre-Sprint Protocol (applies to every sprint)
Before starting any sprint, the agent must do this in order:
1. Read AGENTS entry file.
2. Read current project status.
3. Read previous plan files from knowledge/plan/.
4. Read current sprint ticket file and dependent service docs.
5. Create a new sprint plan file using the naming convention.
6. Start implementation only after the plan is created.

## Docs Reviewed For This Plan
- Knowledge/AGENTS.md
- Knowledge/agent-sync/ai-project-status.md
- Knowledge/agent-sync/ai-rules.md
- Knowledge/BRD.md
- Knowledge/SRS.md
- Knowledge/project-features.md
- Knowledge/how-services-connect.md
- Knowledge/architecture/data-model.md
- Knowledge/reference/api-spec.md
- Knowledge/services/app.md
- Knowledge/services/worker.md
- Knowledge/services/agent.md
- Knowledge/services/om-client.md
- Knowledge/sprint-tickets/sprint-1.md

## Current State Snapshot
- Current sprint in status file: Sprint 1 (Foundation)
- Ticket state: all Sprint 1 tickets not started
- Project artifact state: core runtime files not created yet
- Main goal now: make webhook -> Celery -> agent stub -> DB -> dashboard list work end-to-end

## Sprint 1 Goal
Build a runnable skeleton where:
- POST /webhook/openmetadata queues an RCA task.
- Worker executes stub agent flow.
- Incident is persisted in PostgreSQL.
- Dashboard list page shows incidents.
- Health and metrics endpoints are available.

## Locked Constraints
- Respect module dependency chain: app -> worker -> agent -> om_client.
- Do not run agent logic in webhook route.
- Keep webhook response fast (queue and return).
- Use locked stack and coding standards from ai-rules and development guidelines.

## Execution Plan (Ticket Order)

### Wave A (critical foundations)
1. DLD-001 Project scaffold + Docker Compose
2. DLD-002 Config + pydantic-settings
3. DLD-003 SQLAlchemy models + Alembic init
4. DLD-005 Celery app + rca_task stub
5. DLD-006 OMClient skeleton + auth

### Wave B (parallelizable after Wave A)
1. DLD-004 Webhook endpoint
2. DLD-007 Agent loop skeleton
3. DLD-008 Dashboard list page
4. DLD-009 Health + metrics endpoints

### Wave C (integration gate)
1. DLD-010 End-to-end flow and quality gates

## Verification Gates
Sprint 1 is complete only if all pass:
1. make dev
2. make migrate
3. trigger demo webhook and incident reaches COMPLETE state
4. make test (target >= 15 tests)
5. make lint (zero ruff errors)
6. GET /health returns OK
7. GET /metrics returns Prometheus output

## Deliverables By End Of Sprint 1
- Runtime scaffolding and container setup
- Database schema and migration
- Working webhook queueing path
- Working Celery task with stub RCA report
- Dashboard incidents list page
- Health and metrics routes

## Risk Controls
1. Docker stack startup failures: validate container health before feature debugging.
2. DB migration drift: keep model imports and alembic env target metadata aligned.
3. Slow webhook path: enforce queue-only behavior in route handler.
4. Coupling violations: check imports after each major ticket.

## Post-Sprint Traceability Update (mandatory)
After Sprint 1 completes:
1. Update Knowledge/sprint-tickets/sprint-1.md with section:

### Agent Plan Traceability
- Plan ID: agent-plan-sprint-1-1
- Completion date: YYYY-MM-DD
- Covered tickets: DLD-001 to DLD-010
- Major decisions: <short bullets>
- Deviations from plan: <none or details>

2. Update Knowledge/agent-sync/ai-project-status.md under Decisions Made This Session:
- Sprint 1 completed via agent-plan-sprint-1-1.

## Next Plan Trigger
Before Sprint 2 starts, create next plan:
- knowledge/plan/agent-plan-sprint-2-1.md
- It must review this file, latest status, Sprint 2 ticket file, and any new docs/decisions.
