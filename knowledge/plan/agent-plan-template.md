# Agent Plan: [Sprint Number or Core Essence]

## Plan Metadata
- Plan ID: agent-plan-[sprint-number-or-core-essence]-[number]
- Date: [YYYY-MM-DD]
- Sprint: [1|2|3|4|5 or N/A for non-sprint plan]
- Plan Type: [Sprint kickoff | Core setup | Recovery | Replan]
- Naming convention: knowledge/plan/agent-plan-[sprint-number-or-core-essence]-[number].md
- Previous plans reviewed:
  - [knowledge/plan/agent-plan-...]
  - [knowledge/plan/agent-plan-...]

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
- [Knowledge/AGENTS.md]
- [Knowledge/agent-sync/ai-project-status.md]
- [Knowledge/agent-sync/ai-rules.md]
- [Knowledge/BRD.md]
- [Knowledge/SRS.md]
- [Knowledge/project-features.md]
- [Knowledge/how-services-connect.md]
- [Knowledge/architecture/data-model.md]
- [Knowledge/reference/api-spec.md]
- [Knowledge/services/app.md]
- [Knowledge/services/worker.md]
- [Knowledge/services/agent.md]
- [Knowledge/services/om-client.md]
- [Knowledge/sprint-tickets/sprint-[N].md]

## Current State Snapshot
- Current sprint in status file: [value]
- Ticket state summary: [not started / in progress / mixed]
- Completed work carried in: [summary]
- Blockers carried in: [none or list]
- Main objective now: [one-line objective]

## Scope
### In Scope
- [item]
- [item]

### Out of Scope
- [item]
- [item]

## Locked Constraints
- Respect module dependency chain: app -> worker -> agent -> om_client.
- Keep webhook route queue-only and fast.
- Follow locked stack and coding rules from ai-rules and guidelines.
- Preserve MVP boundaries unless explicitly re-scoped.

## Execution Plan

### Wave A (Foundational / Blocking)
1. [Ticket ID] [Title]
2. [Ticket ID] [Title]
3. [Ticket ID] [Title]

### Wave B (Parallelizable)
1. [Ticket ID] [Title]
2. [Ticket ID] [Title]
3. [Ticket ID] [Title]

### Wave C (Integration / Gate)
1. [Ticket ID] [Title]
2. [Ticket ID] [Title]

## Ticket-Level Plan Table
| Ticket | Outcome | Dependencies | Acceptance Gate |
|---|---|---|---|
| [ID] | [short outcome] | [ID list] | [test or check] |
| [ID] | [short outcome] | [ID list] | [test or check] |

## Verification Gates (Definition of Done)
Plan/sprint is complete only if all required checks pass:
1. [build/run command]
2. [migration check]
3. [functional end-to-end check]
4. [test command and target]
5. [lint/type checks]
6. [observability/health checks]

## Deliverables
- [artifact/output]
- [artifact/output]
- [artifact/output]

## Risk Register
1. Risk: [description]
   - Impact: [high/med/low]
   - Mitigation: [action]
2. Risk: [description]
   - Impact: [high/med/low]
   - Mitigation: [action]

## Change Control
If major deviation happens:
1. Record deviation in this file under Deviations.
2. If re-planning is needed, create next numbered plan file.
3. Reference superseded plan and reason.

## Deviations
- [none yet]

## Mandatory Traceability Updates After Sprint Completion
1. Update sprint ticket file:
   - File: Knowledge/sprint-tickets/sprint-[N].md
   - Add section:

### Agent Plan Traceability
- Plan ID: [agent-plan-...]
- Completion date: [YYYY-MM-DD]
- Covered tickets: [ID range/list]
- Major decisions: [bullets]
- Deviations from plan: [none/details]

2. Update project status file:
   - File: Knowledge/agent-sync/ai-project-status.md
   - Add line under Decisions Made This Session:
   - Sprint [N] completed via [agent-plan-...].

## Next Plan Trigger
Before next sprint starts:
1. Re-read AGENTS, status, previous plans, next sprint ticket file.
2. Create: knowledge/plan/agent-plan-[next-sprint-or-core-essence]-[number].md
3. Carry forward unresolved risks and blockers.
