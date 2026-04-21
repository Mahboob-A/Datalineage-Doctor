# Business Requirements Document

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Author:** Mehboob (Solo Developer)
**Status:** Approved

---

## Project Overview

DataLineage Doctor is an autonomous AI agent that performs root cause analysis (RCA) on data quality incidents. When an OpenMetadata data quality test fails, the agent traverses the metadata knowledge graph, identifies the upstream root cause, calculates the downstream blast radius, and delivers a structured incident report — automatically, without manual intervention.

It serves data engineers and data teams who operate pipelines governed by OpenMetadata and need fast, reliable answers when data breaks.

---

## Problem Statement

When a data quality test fails in a modern data platform, the on-call data engineer faces a predictable crisis: they know something is broken, but not where, why, or how far the damage has spread. Diagnosing the root cause requires opening OpenMetadata to trace lineage, cross-referencing pipeline logs, correlating timestamps, checking owner contacts, and manually estimating which downstream dashboards and models are affected. This process takes between 90 minutes and 3 hours on average.

The pain is compounded by context switching across tools, the cognitive load of building a mental lineage model under pressure, and the risk that the blast radius is larger than estimated. Teams that experience recurring incidents must repeat this process every time with no institutional memory to accelerate future responses.

DataLineage Doctor exists to compress this diagnostic window from hours to minutes.

---

## Stakeholders and Users

| Role | Type | Relationship to Product |
|---|---|---|
| Data Engineer (on-call) | Primary user | Receives automated Slack notification and reads the RCA report during an incident |
| Data Team Lead | Secondary user | Reviews the dashboard to track incident history and blast radius patterns |
| Data Platform Owner | Secondary stakeholder | Benefits from reduced incident MTTR and improved team confidence in the platform |
| ML Engineer | Secondary user | Is notified when an upstream table feeding an ML feature pipeline is implicated |
| Hackathon Judges | Evaluator | Assesses impact, novelty, technical depth, and working demo quality |
| Solo Developer | Builder | Designs, implements, tests, and demos the full system within 10 days |

---

## Goals and Success Metrics

### Primary Goal

Eliminate manual root cause analysis for data quality incidents by delivering a structured, confidence-scored RCA report within 10 minutes of a test failure.

### Success Metrics

| Metric | Target |
|---|---|
| Time from `testCaseFailed` webhook to Slack notification | ≤ 10 minutes |
| End-to-end RCA completion time (agent loop) | ≤ 3 minutes |
| Blast radius correctly identified (demo pipeline) | 100% of downstream consumers |
| Confidence score produced for every incident | Yes |
| `make demo` succeeds from cold start | Yes, reproducibly |
| Test suite | ≥ 50 passing tests |
| Dashboard renders incident detail with lineage graph | Yes |
| Prometheus metrics live during demo | Yes |

---

## Constraints

| Constraint | Detail |
|---|---|
| Timeline | 10 days (April 17–26, 2026) |
| Team size | Solo developer |
| Deployment target | Local Docker Compose only; no cloud deployment required |
| LLM budget | Budget-class models — Gemini, DeepSeek, Kimi, GLM, or any OpenAI-compatible model |
| OpenMetadata | Self-hosted, Docker, assumes lineage and DQ tests are already configured in the demo environment |
| External services | Slack (webhook URL) and OpenMetadata only; no other SaaS integrations |
| Demo data | Synthetic — seeded by `scripts/seed_demo.py` |
| Infrastructure | Docker Compose: FastAPI app, Celery worker, Redis, PostgreSQL, OpenMetadata stack |

---

## Assumptions

- OpenMetadata is running and accessible on the local Docker network during development and demo.
- Lineage relationships between demo tables are pre-seeded by the provided seed script.
- At least one DQ test suite exists in the demo OpenMetadata instance before the trigger script runs.
- The LLM API key is valid and the configured model supports OpenAI-compatible tool calling.
- Slack webhook URL is provided as an environment variable; delivery is fire-and-forget.
- PostgreSQL credentials are managed via environment variables; no external secret manager is required for MVP.
- The dashboard is not publicly accessible; it is a localhost demo tool only.
- Users interacting with the dashboard have no authentication requirement in MVP.

---

## Out of Scope

The following are explicitly not part of this project:

- **User authentication and access control** — the dashboard has no login in MVP
- **Multi-tenant or multi-instance support** — one OpenMetadata instance only
- **Airflow, dbt, or Spark direct integration** — pipeline state is read from OpenMetadata entities only, not from the orchestrators themselves
- **Real-time streaming lineage** — lineage is read from OpenMetadata at query time, not streamed
- **Email or PagerDuty notifications** — Slack only
- **Automated remediation** — the agent diagnoses and recommends, it does not execute fixes
- **Production deployment infrastructure** — no Kubernetes, Helm, or cloud provider config
- **Mobile or responsive dashboard** — desktop-only Jinja2 dashboard
- **Historical trend analytics or aggregation** — the dashboard shows incidents, not trend reports
- **AI-generated lineage or schema suggestions** — the agent reads existing metadata, it does not generate new metadata
- **Support for non-OpenMetadata metadata stores** — the system is OpenMetadata-native
