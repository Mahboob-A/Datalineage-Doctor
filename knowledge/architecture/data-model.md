# Data Model

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Storage Overview

DataLineage Doctor uses **PostgreSQL 16** as its local persistence layer, managed via **SQLAlchemy 2.0** (async ORM) and **Alembic** for migrations. There is no ORM for OpenMetadata data — that is fetched live via `om_client` at query time.

The local database stores only what DataLineage Doctor produces: RCA incidents, their timeline events, blast radius consumers, and tool call logs. Everything else (lineage graphs, DQ test results, entity metadata) is owned by OpenMetadata and queried on demand.

**Database name:** `datalineage_doctor`
**Connection:** `postgresql+psycopg://dld:dld@db:5432/datalineage_doctor`

---

## Entity Relationship Overview

```
incidents (1)
    ├── timeline_events (many)
    ├── blast_radius_consumers (many)
    └── tool_call_logs (many)
```

All child tables carry a `incident_id` foreign key back to `incidents`. Cascade delete is enabled — deleting an incident removes all its children.

---

## Table: `incidents`

The primary record for each RCA run. One row per `testCaseFailed` event that is fully processed.

### SQLAlchemy Model

```python
class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    table_fqn: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    test_case_fqn: Mapped[str] = mapped_column(String(512), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus), nullable=False, default=IncidentStatus.PROCESSING
    )
    root_cause_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_chain: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    remediation_steps: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[ConfidenceLabel | None] = mapped_column(
        SQLEnum(ConfidenceLabel), nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    om_incident_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    timeline_events: Mapped[list["TimelineEvent"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    blast_radius_consumers: Mapped[list["BlastRadiusConsumer"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    tool_call_logs: Mapped[list["ToolCallLog"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
```

### Column Reference

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key, auto-generated |
| `table_fqn` | VARCHAR(512) | No | The failing table, indexed for history lookup |
| `test_case_fqn` | VARCHAR(512) | No | The specific failing test case |
| `triggered_at` | TIMESTAMPTZ | No | When the webhook was received, indexed |
| `completed_at` | TIMESTAMPTZ | Yes | When the agent finished; null while processing |
| `status` | ENUM | No | See `IncidentStatus` enum below |
| `root_cause_summary` | TEXT | Yes | Plain-language root cause from the agent |
| `evidence_chain` | JSONB | Yes | Ordered list of reasoning steps (strings) |
| `remediation_steps` | JSONB | Yes | Ordered list of action steps (strings) |
| `confidence_score` | FLOAT | Yes | 0.0 – 1.0; null while processing |
| `confidence_label` | ENUM | Yes | See `ConfidenceLabel` enum below |
| `celery_task_id` | VARCHAR(255) | Yes | Celery task ID for debugging |
| `om_incident_id` | VARCHAR(255) | Yes | OM-assigned incident entity ID after creation |
| `slack_notified` | BOOLEAN | No | True if Slack notification was sent successfully |
| `raw_report` | JSONB | Yes | Full `RCAReport` dict as produced by the agent |

### JSONB Field Structures

**`evidence_chain`**
```json
["Upstream table raw_orders had no new rows since 2026-04-16 03:00 UTC",
 "Pipeline ingest_orders last succeeded at 2026-04-15 22:00 UTC",
 "DQ test null_check_order_id first failed at 2026-04-16 06:00 UTC"]
```

**`remediation_steps`**
```json
["Check pipeline ingest_orders run logs for errors after 2026-04-15 22:00 UTC",
 "Verify source database connectivity from the ingestion host",
 "Re-run the pipeline after resolving the connection issue and validate DQ tests pass"]
```

**`raw_report`**
```json
{
  "root_cause_summary": "...",
  "confidence_score": 0.91,
  "confidence_label": "HIGH",
  "evidence_chain": [...],
  "remediation_steps": [...],
  "upstream_nodes_checked": 4,
  "tool_calls_made": 8,
  "agent_iterations": 4
}
```

---

## Table: `timeline_events`

Chronological events assembled by the agent during its reasoning, describing the chain of failures.

### SQLAlchemy Model

```python
class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_fqn: Mapped[str] = mapped_column(String(512), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="timeline_events")
```

### Column Reference

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID FK | References `incidents.id`; cascade delete |
| `occurred_at` | TIMESTAMPTZ | When this event happened in the data timeline |
| `event_type` | VARCHAR(64) | e.g. `pipeline_failure`, `dq_test_failure`, `schema_change` |
| `entity_fqn` | VARCHAR(512) | The OpenMetadata entity involved |
| `entity_type` | VARCHAR(64) | e.g. `table`, `pipeline`, `testCase` |
| `description` | TEXT | Plain-language description of the event |
| `sequence` | INTEGER | Display order on the dashboard (1 = earliest) |

---

## Table: `blast_radius_consumers`

Each downstream entity identified by the `calculate_blast_radius` tool.

### SQLAlchemy Model

```python
class BlastRadiusConsumer(Base):
    __tablename__ = "blast_radius_consumers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_fqn: Mapped[str] = mapped_column(String(512), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    service: Mapped[str | None] = mapped_column(String(255), nullable=True)

    incident: Mapped["Incident"] = relationship(back_populates="blast_radius_consumers")
```

### Column Reference

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID FK | References `incidents.id`; cascade delete |
| `entity_fqn` | VARCHAR(512) | FQN of the downstream consumer |
| `entity_type` | VARCHAR(64) | e.g. `table`, `dashboard`, `mlmodel` |
| `level` | INTEGER | Distance from the root failing table (1 = direct downstream) |
| `service` | VARCHAR(255) | The service owning this entity (e.g. Metabase, dbt, Feast) |

---

## Table: `tool_call_logs`

Log of every tool call made by the agent during an RCA run. Used for debugging and observability.

### SQLAlchemy Model

```python
class ToolCallLog(Base):
    __tablename__ = "tool_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_args: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)

    incident: Mapped["Incident"] = relationship(back_populates="tool_call_logs")
```

### Column Reference

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `incident_id` | UUID FK | References `incidents.id`; cascade delete |
| `tool_name` | VARCHAR(128) | e.g. `get_upstream_lineage` |
| `called_at` | TIMESTAMPTZ | When the tool call was dispatched |
| `duration_ms` | INTEGER | How long the tool call took |
| `input_args` | JSONB | Arguments passed to the tool function |
| `result_summary` | TEXT | Short description of what was returned |
| `success` | BOOLEAN | False if the tool raised an exception |
| `error_message` | TEXT | Exception message if `success=False` |
| `iteration` | INTEGER | Which loop iteration this call was made in |

---

## Enums

### `IncidentStatus`

```python
class IncidentStatus(str, enum.Enum):
    PROCESSING = "processing"   # Celery task is running
    COMPLETE   = "complete"     # Agent finished, report persisted
    FAILED     = "failed"       # Celery task failed after all retries
```

### `ConfidenceLabel`

```python
class ConfidenceLabel(str, enum.Enum):
    HIGH   = "HIGH"    # confidence_score >= 0.85
    MEDIUM = "MEDIUM"  # 0.60 <= confidence_score < 0.85
    LOW    = "LOW"     # confidence_score < 0.60
```

---

## Indexes

| Table | Column(s) | Type | Reason |
|---|---|---|---|
| `incidents` | `table_fqn` | BTREE | History lookup by table in `find_past_incidents` tool |
| `incidents` | `triggered_at` | BTREE | Dashboard ordering; descending sort |
| `timeline_events` | `incident_id` | BTREE | Join on incident detail page |
| `blast_radius_consumers` | `incident_id` | BTREE | Join on incident detail page |
| `tool_call_logs` | `incident_id` | BTREE | Debug queries per incident |

---

## Migration Notes

- All schema changes go through Alembic revisions — never raw `ALTER TABLE`
- The initial migration creates all four tables plus all enums
- UUID primary keys are generated at the application layer, not by the database
- `JSONB` is used for list-of-strings and dict fields to avoid normalisation overhead for small, rarely-queried structures
- `TIMESTAMPTZ` is used for all timestamps — timezone-aware storage prevents UTC confusion during demo
