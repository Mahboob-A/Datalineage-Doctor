# RCA Domain Data

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Purpose

This document defines the domain concepts, vocabulary, and entity model that the RCA agent reasons about. It also documents the seed dataset used in the demo, the taxonomy of root cause categories, and the confidence scoring rubric. Read this before modifying the agent's system prompt or adding new tools.

---

## Core Domain Concepts

### Fully Qualified Name (FQN)

OpenMetadata identifies every entity with a dot-separated FQN. The structure varies by entity type:

| Entity Type | FQN Pattern | Example |
|---|---|---|
| Table | `service.database.schema.table` | `mysql.default.public.raw_orders` |
| Test Case | `service.database.schema.table.testName` | `mysql.default.public.raw_orders.null_check_order_id` |
| Pipeline | `service.pipeline` | `airflow.ingest_orders_daily` |
| Dashboard | `service.dashboard` | `metabase.revenue_dashboard` |
| ML Model | `service.model` | `feast.churn_prediction_v2` |
| Column | `service.database.schema.table.column` | `mysql.default.public.raw_orders.order_id` |

The agent uses FQNs as entity identifiers in all tool calls and in the `RCAReport` output.

### Lineage Graph

The lineage graph in OpenMetadata is a directed acyclic graph (DAG) of entity relationships. Edges flow from **source → consumer** (upstream → downstream). An entity can have multiple upstream parents and multiple downstream children.

```
mysql.default.raw_orders (source)
        │
        ▼
dbt.default.stg_orders (consumer of raw_orders, source for downstream)
        │
        ▼
dbt.default.fct_orders (consumer of stg_orders, source for downstream)
        │
        ├──▶ metabase.revenue_dashboard
        └──▶ feast.churn_model_features
```

When the agent investigates a failing table, it traverses **upstream** (looking for the cause) and **downstream** (calculating blast radius).

### Data Quality Test Types

OpenMetadata supports these test types that DataLineage Doctor may encounter in webhook events:

| Test Type | `testType` value | What it checks |
|---|---|---|
| Null check | `columnValuesToBeNotNull` | Column has no null values |
| Uniqueness | `columnValuesToBeUnique` | Column values are unique |
| Range | `columnValuesToBeBetween` | Values within min/max bounds |
| Row count | `tableRowCountToBeBetween` | Row count within expected range |
| Freshness | `tableLastModifiedTimeToBeBetween` | Data is recent enough |
| Custom SQL | `tableCustomSQLQuery` | Custom SQL assertion passes |

The most common root-cause-linked test types are **row count** (empty/stale table from a broken pipeline) and **null check** (schema change dropping a NOT NULL column).

### Pipeline Entity

In OpenMetadata, a pipeline entity represents a data pipeline (Airflow DAG, dbt run, Fivetran sync, etc.). It carries:
- `pipelineStatus` — last run status: `Successful`, `Failed`, `Pending`
- `tasks` — list of task runs with individual statuses
- `startDate` / `endDate` — timestamps of the last run

The agent queries pipeline status to correlate pipeline failures with DQ test failures.

---

## Demo Dataset

The seed script (`scripts/seed_demo.py`) creates this entity topology in OpenMetadata:

### Services

| Service Name | Type |
|---|---|
| `mysql` | Database (MySQL) |
| `airflow` | Pipeline (Apache Airflow) |
| `dbt` | Pipeline (dbt) |
| `metabase` | Dashboard (Metabase) |

### Tables

| FQN | Description | Row count (normal) |
|---|---|---|
| `mysql.default.raw_orders` | Source orders table | ~50,000 |
| `mysql.default.raw_products` | Source products table | ~5,000 |
| `dbt.default.stg_orders` | Staged orders (dbt model) | ~50,000 |
| `dbt.default.stg_products` | Staged products | ~5,000 |
| `dbt.default.fct_orders` | Orders fact table | ~50,000 |
| `dbt.default.fct_revenue` | Revenue aggregation | ~365 |

### Lineage Graph (demo)

```
mysql.default.raw_orders  ──────────────┐
                                         ▼
mysql.default.raw_products ──▶  dbt.default.stg_orders ──▶ dbt.default.fct_orders ──▶ metabase.revenue_dashboard
                                         │                                                       │
                                         ▼                                                       ▼
                               dbt.default.stg_products ──▶ dbt.default.fct_revenue    feast.order_value_model
```

### DQ Tests (demo)

| Test FQN | Test Type | Table |
|---|---|---|
| `mysql.default.raw_orders.null_check_order_id` | `columnValuesToBeNotNull` | `raw_orders` |
| `mysql.default.raw_orders.row_count_orders` | `tableRowCountToBeBetween` | `raw_orders` |
| `dbt.default.fct_orders.unique_order_id` | `columnValuesToBeUnique` | `fct_orders` |
| `dbt.default.fct_revenue.freshness_check` | `tableLastModifiedTimeToBeBetween` | `fct_revenue` |

### Demo Failure Scenario

The `scripts/trigger_demo.py` fires a `testCaseFailed` event for `null_check_order_id` on `raw_orders`. The expected agent reasoning path:

1. **Upstream lineage** — finds `raw_orders` has no upstream tables (it is a source). Upstream is clean.
2. **DQ test history** — finds `null_check_order_id` has been passing for 30 days, first failure is today.
3. **Pipeline status** — finds `airflow.ingest_orders_daily` last run **failed** at 03:00 UTC today.
4. **Entity owners** — finds the data engineering team owns `raw_orders`.
5. **Blast radius** — `stg_orders → fct_orders → revenue_dashboard, order_value_model` (4 downstream consumers).
6. **Past incidents** — no prior incidents on this table.
7. **Conclusion** — root cause is pipeline `airflow.ingest_orders_daily` failure causing no new rows, triggering null check failure. Confidence: HIGH.

---

## Root Cause Taxonomy

The agent is guided by the system prompt to classify root causes into one of these categories. The category is embedded in `root_cause_summary` prose — there is no separate `category` field in MVP.

| Category | Description | Typical indicator |
|---|---|---|
| **Pipeline failure** | Upstream pipeline stopped running; data stopped flowing | Pipeline `Failed` status + DQ test failure timestamp correlation |
| **Schema change** | Column added, removed, or renamed in source | Schema change event in OM history + null/uniqueness test failure |
| **Source data issue** | Bad data arrived from an external source | All pipelines healthy; DQ failure on raw source table |
| **Stale data** | Data is too old; freshness test fails | Row count normal; freshness test fails; no pipeline errors |
| **Infrastructure issue** | Database or network connectivity problem | All pipelines show `Failed`; no schema changes |
| **Unknown** | Insufficient evidence to classify | No corroborating evidence found across tools |

---

## Confidence Scoring Rubric

The system prompt instructs the agent to use this rubric when setting `confidence_score`:

| Score range | Label | Criteria |
|---|---|---|
| 0.85 – 1.00 | HIGH | Clear causal chain with 3+ pieces of corroborating evidence; timeline is unambiguous |
| 0.60 – 0.84 | MEDIUM | Likely cause identified but 1–2 supporting signals are absent or ambiguous |
| 0.00 – 0.59 | LOW | Insufficient evidence; OM APIs returned errors or 404s; no timeline can be established |

**Automatic LOW scenarios:**
- The loop hit `MAX_ITERATIONS` (fallback report)
- More than 3 tool calls returned `{"error": ...}` or `{"found": False}`
- No upstream nodes were found AND the pipeline status is unknown

---

## Timeline Event Types

These are the valid values for `TimelineEvent.event_type`:

| Value | Description |
|---|---|
| `pipeline_failure` | A pipeline entity reported a failed run |
| `dq_test_failure` | A DQ test case failed |
| `schema_change` | A schema change was detected on an entity |
| `data_freshness_issue` | Data was last updated longer ago than expected |
| `source_data_anomaly` | Anomalous row count or value distribution in a source table |
| `incident_trigger` | The webhook event that started this investigation |

---

## Blast Radius Entity Types

These are the downstream entity types the agent may include in the blast radius:

| `entity_type` value | What it represents |
|---|---|
| `table` | A downstream table in any service |
| `dashboard` | A BI dashboard (Metabase, Looker, Superset, etc.) |
| `mlmodel` | A machine learning model or feature set |
| `report` | A scheduled report |
| `pipeline` | A downstream pipeline that depends on the failing data |

---

## Vocabulary Quick Reference

| Term | Definition |
|---|---|
| **Root cause** | The earliest entity in the causal chain whose failure triggered the DQ test failure |
| **Blast radius** | The set of downstream entities that are likely affected by the root cause |
| **Evidence chain** | The ordered list of observations the agent made to reach its conclusion |
| **Remediation** | The concrete action steps to resolve the incident |
| **Incident** | A DataLineage Doctor record representing one completed RCA investigation |
| **Confidence** | The agent's self-assessed certainty that its root cause is correct |
| **Upstream** | Entities that provide data to the failing table (causes) |
| **Downstream** | Entities that consume data from the failing table (affected parties) |
