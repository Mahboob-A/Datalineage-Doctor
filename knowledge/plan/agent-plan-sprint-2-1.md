# Agent Plan: Sprint 2 Agent Tools

## Plan Metadata
- Plan ID: agent-plan-sprint-2-1
- Date: April 20, 2026
- Sprint: 2
- Plan Type: Sprint kickoff
- Naming convention: knowledge/plan/agent-plan-[sprint-number-or-core-essence]-[number].md
- Previous plans reviewed:
  - knowledge/plan/agent-plan-sprint-1-1.md

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
- knowledge/agent-sync/ai-project-status.md
- knowledge/agent-sync/ai-rules.md
- knowledge/BRD.md
- knowledge/SRS.md
- knowledge/project-features.md
- knowledge/how-services-connect.md
- knowledge/architecture/data-model.md
- knowledge/reference/api-spec.md
- knowledge/reference/rca-domain-data.md
- knowledge/services/app.md
- knowledge/services/worker.md
- knowledge/services/agent.md
- knowledge/services/om-client.md
- knowledge/sprint-tickets/sprint-2.md
- knowledge/plan/agent-plan-sprint-1-1.md

## Current State Snapshot
- Current sprint in status file: Sprint 2 (Agent Tools)
- Sprint 1 status: completed (DLD-001 to DLD-010)
- Runtime state: Docker is available, and stack startup/testing can continue in-container
- Main goal now: replace stubs with real OpenMetadata-backed RCA tooling and a real LLM loop

## Sprint 2 Goal
Build and test all 6 RCA tools so the agent can produce real RCA reports from seeded OpenMetadata data.

Expected sprint outcome:
- Real tool-calling LLM loop with parser and retries.
- Working tools for lineage, DQ history, pipeline status, ownership, blast radius, and past incidents.
- Deterministic seed script for demo topology.
- End-to-end incident flow producing a HIGH-confidence non-stub report.

## Locked Constraints
- Respect module dependency chain: app -> worker -> agent -> om_client.
- Keep webhook route queue-only and fast.
- Use locked stack and coding standards from ai-rules and development guidelines.
- Confidence label must be recalculated from score in parser (HIGH when score >= 0.85).
- Mock LLM in automated tests; use real LLM only for final smoke test.

## Execution Plan (Ticket Order)

### Wave A (blocking foundation)
1. DLD-011 Real Agent Loop (LLM Integration)

### Wave B (parallelizable after Wave A)
1. DLD-012 Tool: get_upstream_lineage
2. DLD-013 Tool: get_dq_test_results
3. DLD-014 Tool: get_pipeline_entity_status
4. DLD-015 Tool: get_entity_owners
5. DLD-016 Tool: calculate_blast_radius
6. DLD-017 Tool: find_past_incidents

### Wave C (integration and demo gate)
1. DLD-018 Demo Seed Script
2. DLD-019 End-to-End Real Agent Smoke Test

## Ticket-Level Plan Table
| Ticket | Outcome | Dependencies | Acceptance Gate |
|---|---|---|---|
| DLD-011 | Replace loop stub with real tool-calling LLM loop + parser + retries + tool_call_logs | DLD-007, DLD-006 | tests/test_agent_loop.py passes stop/tool_calls/max-iteration paths |
| DLD-012 | Upstream lineage tool and OM lineage client implementation | DLD-011, DLD-006 | tests/test_tools_lineage.py passes success/not-found/error |
| DLD-013 | DQ result history tool and OM quality client implementation | DLD-011, DLD-006 | tests/test_tools_quality.py passes success/not-found/mixed results |
| DLD-014 | Pipeline status tool and OM pipeline client implementation | DLD-011, DLD-006 | tests/test_tools_pipeline.py passes success/failed/not-found |
| DLD-015 | Ownership tool and OM ownership client implementation | DLD-011, DLD-006 | tests/test_tools_ownership.py passes owner/no-owner/not-found |
| DLD-016 | Blast radius downstream traversal and sorting | DLD-012 | tests/test_tools_lineage.py blast radius cases pass |
| DLD-017 | Past incident lookup from local DB by table_fqn | DLD-003, DLD-011 | tests/test_tools_history.py passes with seeded DB rows |
| DLD-018 | Idempotent OM seed script for demo topology | DLD-006, DLD-012..016 | uv run python scripts/seed_demo.py succeeds twice without duplicates |
| DLD-019 | Real end-to-end smoke run with seeded OM and live LLM | DLD-011..018 | incident completes with HIGH confidence and non-stub root cause |

## Verification Gates
Sprint 2 is complete only if all pass:
1. uv run pytest tests -q (target: >= 35 tests total)
2. uv run ruff check .
3. uv run python scripts/seed_demo.py runs successfully and idempotently
4. uv run python scripts/trigger_demo.py triggers a complete incident within 3 minutes
5. Dashboard incident has non-stub root cause summary and confidence_label HIGH
6. Incident has at least 3 timeline events and at least 2 blast radius consumers
7. GET /metrics includes successful RCA request increment

## Deliverables By End Of Sprint 2
- Real agent loop with parser and retry behavior.
- Fully implemented OM-backed tools (lineage, quality, pipeline, ownership, blast radius).
- Implemented DB-backed past incidents tool.
- Seed script for deterministic demo topology.
- Passing test/lint gates and validated end-to-end incident flow.

## Risk Controls
1. LLM response formatting risk (invalid JSON)
   - Mitigation: robust parser extraction and one correction pass.
2. OpenMetadata API shape drift or partial data
   - Mitigation: graceful defaults for not-found/missing fields and targeted test fixtures.
3. Slow or flaky live LLM during development
   - Mitigation: mock LLM in tests, reserve live model for final smoke test.
4. Seed script duplication risk
   - Mitigation: idempotent create-or-skip logic by FQN.
5. Heavy compose stack startup overhead
   - Mitigation: keep compose profile lean for Sprint 2 work and avoid unnecessary services.

## Post-Sprint Traceability Update (mandatory)
After Sprint 2 completes:
1. Update knowledge/sprint-tickets/sprint-2.md with section:

### Agent Plan Traceability
- Plan ID: agent-plan-sprint-2-1
- Completion date: YYYY-MM-DD
- Covered tickets: DLD-011 to DLD-019
- Major decisions:
  - Confidence label derived from score in parser.
  - Mocked LLM for tests, real LLM for smoke run.
  - Prioritize a lean compose runtime for sprint velocity.
- Deviations from plan: <none or details>

2. Update knowledge/agent-sync/ai-project-status.md under Decisions Made This Session:
- Sprint 2 completed via agent-plan-sprint-2-1.

## Execution Outcome Update

### Status As Of 2026-04-22
- Sprint 2 is fully closed.
- DLD-011 through DLD-019 are complete.

### What Was Successfully Delivered
- Real tool-calling LLM loop, parser integration, retries, and tool-call logging.
- All six real RCA tools from DLD-012 through DLD-017.
- Live OpenMetadata runtime validation for the demo seed script.
- True idempotency for `scripts/seed_demo.py`.
- End-to-end queue, worker, OpenMetadata access, DB persistence, and metrics validation path.
- Live Gemini 2.5 Flash smoke validation producing a real HIGH-confidence RCA.

### What Failed Relative To Plan
- The only material closure issue was a temporary OpenMetadata auth failure after the stack restarted.

### Why DLD-019 Failed
- The original blocker was the previous provider's context ceiling.
- After switching the live path to Gemini 2.5 Flash, the remaining issue was a stale OpenMetadata JWT causing temporary `401 Unauthorized` responses.
- Refreshing the JWT and recreating `app` and `worker` cleared the blocker.

### Deviations From Plan
- The plan assumed DLD-019 would be the final smoke gate after DLD-018 and would pass once the runtime was healthy.
- In execution, additional work was required after DLD-018 to restore OM auth, to make `scripts/seed_demo.py` truly idempotent, and to switch the live smoke path to Gemini 2.5 Flash.
- A small regression in `tests/test_agent_loop.py` was also corrected so the cached-tool-call assertion matches the current loop message text.

### Immediate Next Step
- Start Sprint 3 using `knowledge/plan/agent-plan-sprint-3-1.md`.

## Next Plan Trigger
Before Sprint 3 starts, create next plan:
- knowledge/plan/agent-plan-sprint-3-1.md
- It must review this file, latest status, Sprint 3 ticket file, and any new docs/decisions.
