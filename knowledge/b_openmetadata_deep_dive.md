# OpenMetadata: The Complete Deep Dive
### From Zero to Expert — Everything You Need for the Hackathon

---

## 1. The Problem OpenMetadata Solves

Imagine a company with 500 engineers, 200 data analysts, 50 data pipelines, 30 dashboards, 10 databases, and 3 data warehouses. Every day, a new analyst joins and asks:

> *"What does the `user_lifetime_value` column in `analytics.users` mean?"*
> *"Which dashboard broke when someone changed the `orders` table?"*
> *"Does this table have any PII? Who owns it? Was it updated recently?"*
> *"Is this data trustworthy? When was the last quality check?"*

Without a metadata platform, the answers to these questions live in:
- Slack messages that get buried
- Confluence pages that are 2 years out of date
- The head of the one engineer who designed it (who left 6 months ago)
- Nowhere at all

**This is the metadata problem.** It silently costs companies millions in wasted analyst hours, broken pipelines, compliance fines, and wrong business decisions made on bad data.

**OpenMetadata is the solution** — a single platform that automatically discovers, catalogs, documents, monitors, and governs all your data assets.

---

## 2. What Is OpenMetadata? (Precise Definition)

OpenMetadata is an **open-source, unified metadata platform** that acts as a central nervous system for all data in an organization. It was:

- **Founded:** 2021 by Suresh Srinivas (ex-Hortonworks/Apache Atlas) and team
- **Inspired by:** Uber's internal metadata infrastructure
- **Company behind it:** Collate (YC W22)
- **GitHub:** 6,000+ stars, 300+ contributors
- **Connectors:** 90+ (databases, warehouses, BI tools, ML platforms, pipelines, messaging)

It is **not** a data warehouse. It is **not** a BI tool. It is **not** a database.

It is the **catalog and control plane** that sits on top of all your data systems.

---

## 3. The Four Core Pillars

### 3.1 Data Discovery
*"Find the right data, fast."*

- Full-text search across all data assets (tables, dashboards, pipelines, ML models, topics)
- Rich entity pages: schema, description, sample data, column-level documentation
- Business glossary: define "Active User" once, link it to every column that represents it
- Tiering system: mark which datasets are critical ("Tier 1") vs experimental ("Tier 3")
- Data products: group related assets into logical products with owners
- Usage analytics: see which tables are actually being queried

### 3.2 Data Lineage
*"Understand where data comes from and where it goes."*

- **Column-level lineage**: not just "Table A → Table B" but "Column X in Table A → Column Y in Table B via transformation Z"
- Automatically captured from: Airflow, dbt, Spark, Flink, Glue, and more
- Manually editable when automation misses something
- Upstream/downstream impact analysis: "If I change this column, what dashboards break?"
- Pipeline visualization: visual graph of your entire data flow

### 3.3 Data Observability
*"Know when your data is broken before your users do."*

- **Data Quality Tests:** define expectations on columns (not null, unique, value range, custom SQL)
- Test suites that run on schedule via the Ingestion Framework
- Anomaly detection on table row counts, column statistics, freshness
- Incident management: log, track, and resolve data incidents
- Data SLAs: set freshness and quality commitments per dataset
- Alerting: webhook, Slack, MS Teams, email notifications when tests fail

### 3.4 Data Governance
*"Control who can see what, and ensure compliance."*

- **Auto-classification:** automatically tag columns containing PII (email, phone, SSN, credit card)
- Tag hierarchy: create custom taxonomies (Confidential > PII > Email)
- RBAC: fine-grained role-based access control at table/column level
- Data policies: who can view/edit/own what
- Audit logs: every access and change is tracked
- GDPR/HIPAA compliance tooling: find all PII, see who accessed it
- Ownership: assign data owners, stewards, experts to every asset

---

## 4. Technical Architecture (For Builders)

OpenMetadata has a deliberately **simple 4-component architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenMetadata Platform                     │
│                                                              │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │  API Server   │  │  Metadata Store  │  │  Search Index  │ │
│  │  (Java/      │  │  (MySQL/         │  │  (Elasticsearch│ │
│  │  Dropwizard) │  │   PostgreSQL)    │  │   / OpenSearch)│ │
│  └──────────────┘  └─────────────────┘  └────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Ingestion Framework (Python)               │   │
│  │  Connectors → Transformers → Sink → OpenMetadata API │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Web UI    │  │  MCP Server  │  │  Workflow           │  │
│  │  (React)   │  │  (Built-in)  │  │  Orchestrator      │  │
│  └────────────┘  └──────────────┘  │  (Airflow/K8s)     │  │
│                                    └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### API Server
- Java + Dropwizard
- REST API for all metadata CRUD operations
- JWT authentication
- Every entity (Table, Dashboard, Pipeline, User, Glossary, Tag...) has typed API endpoints
- OpenAPI spec available at `/api/v1/openapi`

### Metadata Store
- MySQL or PostgreSQL
- Stores the **metadata graph** — entities + their relationships
- Entities are JSON documents validated against JSON Schema definitions
- Relationships are first-class: Table "owns" Columns, Dashboard "uses" Table, User "owns" Table

### Search Index
- Elasticsearch or OpenSearch
- Powers the discovery UI's full-text search
- Automatically synced when metadata changes

### Ingestion Framework
- Python library: `openmetadata-ingestion`
- Connector → Stage → Bulk Sink pipeline
- Each connector extracts metadata from a source (e.g., PostgreSQL tables + schemas)
- Transformers enrich the metadata (add descriptions, tags, lineage)
- Sink writes to the API Server
- Can be scheduled via: built-in scheduler, Airflow, Prefect, Dagster, Kubernetes

### MCP Server
- Built into OpenMetadata (since mid-2025)
- Exposes the entire Unified Knowledge Graph to LLMs via MCP protocol
- Tools available: search assets, get lineage, read/write glossary, create quality tests, update descriptions, etc.
- Uses the same RBAC as the REST API (bot tokens or PAT)

---

## 5. The Unified Knowledge Graph

The most powerful concept in OpenMetadata is the **Unified Knowledge Graph** — a connected graph where every data artifact is a node and relationships are edges.

**Entities (nodes):**
- Tables, Columns, Databases, Schemas
- Dashboards, Charts, Reports
- Pipelines, Tasks, DAGs
- ML Models, ML Features
- Topics (Kafka/messaging)
- API Collections, API Endpoints
- Users, Teams, Roles
- Glossary Terms, Tags
- Data Products, Domains

**Relationships (edges):**
- `Table` → has → `Columns`
- `Column` → tagged as → `PII > Email`
- `Dashboard` → lineage from → `Table`
- `Pipeline` → produces → `Table`
- `User` → owns → `Table`
- `Glossary Term` → describes → `Column`
- `Test Case` → validates → `Table`
- `Incident` → affects → `Table`

This graph is what makes OpenMetadata so powerful for AI agents — one query can traverse the entire organizational data knowledge.

---

## 6. How Industry Is Using OpenMetadata

### Financial Services
- **Use case:** Regulatory compliance (BCBS 239, GDPR, SOX)
- Auto-classify all PII columns across 500+ tables
- Maintain data lineage for audit trails ("where did this number in the regulatory report come from?")
- Enforce ownership: every table must have a named data steward
- Real companies: banks, insurance firms, payment processors

### E-Commerce / Retail
- **Use case:** Data democratization + quality
- Analysts self-serve data discovery instead of asking data engineers
- Data quality tests catch broken ETL pipelines before dashboards go wrong
- Business glossary standardizes "conversion rate" definition across 12 teams who all calculated it differently

### Healthcare
- **Use case:** HIPAA compliance + data trust
- Auto-tag PHI (Protected Health Information) columns
- Lineage tracks patient data from source systems to analytics
- Access controls prevent unauthorized querying of sensitive patient records

### Tech Companies / SaaS
- **Use case:** Data platform maturity
- Data products with clear ownership
- Self-service analytics where engineers + analysts find their own data
- Cost optimization: identify and deprecate unused tables (usage analytics)

### Startups (Growing Data Teams)
- **Use case:** Getting organized before it's too late
- Even 10-person teams benefit from documented tables and clear ownership
- Prevents the "tribal knowledge" problem when engineers leave

---

## 7. AI-Native Applications with OpenMetadata

This is where it gets exciting for the hackathon. OpenMetadata + AI opens up entirely new categories of applications.

### Pattern 1: Conversational Data Discovery
An agent that answers: *"What's our most used table for revenue analytics?"*
- Agent calls OpenMetadata MCP → search_assets(query="revenue analytics")
- Gets back table entities with usage stats
- Returns human-readable answer with lineage context

### Pattern 2: Auto-Documentation Agent
An agent that reads table schemas + sample data and generates:
- Column descriptions
- Table-level summaries
- Business glossary entries
- Detected data patterns (this looks like a fact table, this looks like a dimension)
Writes everything back to OpenMetadata via API/MCP.

### Pattern 3: Impact Analysis Agent
User says: *"I need to change the `user_id` column in `users` table from INT to UUID"*
- Agent traces all downstream dependencies via lineage
- Finds: 12 tables, 3 dashboards, 2 ML models that use this column
- Generates a migration impact report
- Suggests a rollout plan

### Pattern 4: Governance Enforcement Agent
Continuously monitors OpenMetadata for policy violations:
- Tables without owners → auto-assign based on team/domain rules
- Columns matching PII patterns → auto-tag + notify data steward
- Tables without quality tests → create default test suite
- Assets missing descriptions → queue for auto-documentation

### Pattern 5: Data Quality Debugger Agent
When a data quality test fails:
- Agent fetches the failing test details
- Looks up lineage: which pipeline produced this table?
- Checks pipeline run history for recent changes
- Searches for similar incidents in history
- Generates root cause analysis + suggested fix

### Pattern 6: Natural Language → SQL + Context
User asks a natural language question → agent:
1. Finds relevant tables via OpenMetadata search
2. Reads schema + column descriptions + glossary terms
3. Generates SQL with full semantic understanding (not just column names, but what they MEAN)
4. Executes against the database
5. Returns results with provenance ("this answer came from `analytics.orders`, owned by Data Platform team, last tested 2 hours ago, quality: ✅")

---

## 8. Hidden Possibilities & Unexplored Use Cases

These are the **non-obvious applications** that most people haven't thought of yet:

### 8.1 Metadata as a Feature Store for ML
Columns in OpenMetadata have type information, statistics, lineage, and quality scores.
→ Use this as a **feature catalog** for ML models: which features are trustworthy? Which are stale?
→ Link ML model entities to their training data lineage
→ Auto-detect when training data distribution shifts (data drift = model drift)

### 8.2 Incident Command Center
When a data incident happens (broken pipeline, wrong numbers in CEO's dashboard):
→ OpenMetadata knows the lineage
→ An agent can immediately identify the "blast radius" — every downstream consumer affected
→ Auto-create an incident record, notify all owners, generate a timeline
→ Track resolution and capture the post-mortem in OpenMetadata

### 8.3 Data Contract Enforcement
Data contracts (agreements between data producers and consumers about schema + quality) are a hot concept:
→ Store data contracts as metadata artifacts in OpenMetadata
→ Run quality tests that enforce the contract
→ Alert consumers when a producer violates the contract
→ Lineage shows which consumers are affected by violations

### 8.4 FinOps for Data
OpenMetadata knows which tables are used, how often, by whom, and how large they are:
→ Identify "zombie tables" — large tables that nobody queries
→ Calculate storage + compute cost per table
→ Recommend archival or deletion of expensive, unused data
→ Show which dashboards are the most expensive to refresh

### 8.5 Semantic Search Layer for RAG Applications
Organizations building internal RAG (Retrieval Augmented Generation) chatbots face the "what context to inject?" problem:
→ OpenMetadata's knowledge graph is the perfect index for a data-aware RAG system
→ User asks a business question → find the right tables → find the right rows → answer with grounded data
→ OpenMetadata provides: schema understanding, ownership, freshness, quality score — all as retrieval context

### 8.6 Metadata-Driven Test Generation
For any new table ingested into OpenMetadata:
→ AI agent analyzes schema + sample data + column names
→ Automatically generates a comprehensive test suite (not null, range, unique, referential integrity)
→ Submits tests via API to run on a schedule
→ Zero-manual-effort data quality from day one

### 8.7 Code ↔ Data Lineage Bridge
Most lineage tools stop at the SQL layer. But data often originates in application code:
→ Parse application code (Python, Java) to extract database writes
→ Ingest this as source-level lineage into OpenMetadata
→ Now lineage goes from Git commit → application code → database table → warehouse → dashboard
→ Full software-to-insight provenance

### 8.8 Multi-Org Metadata Federation
Enterprises often have multiple OpenMetadata instances (one per business unit):
→ A federation layer that aggregates metadata across instances
→ Search and governance across org boundaries
→ Useful for M&A scenarios, conglomerate enterprises, or data marketplace platforms

### 8.9 Developer Inner Loop Integration
Most metadata tools are for data teams. What about software engineers?
→ IDE plugin: as a dev writes SQL, autocomplete using actual column descriptions from OpenMetadata
→ Pre-commit hook: if a migration changes a column tagged PII, warn the developer
→ PR description auto-generation: "this PR affects table X (owned by Data Platform), downstream consumers: Dashboard Y"

### 8.10 Agri / Rural Sector Metadata
This is truly unexplored:
→ Government agricultural databases (crop yield, soil health, weather, mandi prices) are often siloed
→ An OpenMetadata deployment that catalogs India's open agricultural datasets
→ Farmers/NGOs/agritech startups discover the right dataset via natural language
→ Lineage connects raw sensor data → processed analytics → government reports

---

## 9. OpenMetadata API Cheat Sheet (For Developers)

### Authentication
```bash
# Get JWT token
POST /api/v1/users/login
{ "email": "admin@open-metadata.org", "password": "..." }
# Returns: { "accessToken": "eyJ..." }

# Use in headers
Authorization: Bearer eyJ...
```

### Core Entity Operations
```bash
# Search everything
GET /api/v1/search/query?q=revenue&index=table_search_index&limit=10

# Get a table
GET /api/v1/tables/fully.qualified.name/tableName
GET /api/v1/tables/{id}?fields=columns,tags,owners,lineage

# List tables in a schema
GET /api/v1/tables?database=my_db&limit=50

# Update description
PATCH /api/v1/tables/{id}
[{ "op": "add", "path": "/description", "value": "This table contains..." }]

# Tag a column with PII
PATCH /api/v1/tables/{id}
[{ "op": "add", "path": "/columns/0/tags", "value": [{"tagFQN": "PII.Sensitive"}] }]
```

### Lineage
```bash
# Get upstream + downstream lineage
GET /api/v1/lineage/table/{id}?upstreamDepth=3&downstreamDepth=3

# Add lineage manually
PUT /api/v1/lineage
{
  "edge": {
    "fromEntity": { "type": "table", "id": "..." },
    "toEntity": { "type": "table", "id": "..." }
  }
}
```

### Data Quality
```bash
# Create a test definition
POST /api/v1/dataQuality/testDefinitions
{ "name": "columnNotNull", "testPlatforms": ["OpenMetadata"], ... }

# Create test case for a column
POST /api/v1/dataQuality/testCases
{ "name": "users_email_not_null", "entityLink": "<#E::table::db.users::email>", ... }

# Get test results
GET /api/v1/dataQuality/testCases/{id}/testCaseResult
```

### MCP Tools (when using MCP server)
- `search_metadata` — full-text search across all entities
- `get_table_details` — schema, columns, owners, tags for a table
- `get_lineage` — upstream/downstream graph for any entity
- `search_glossary` — find business terms and their definitions
- `create_or_update_description` — write descriptions back
- `add_tag` — apply tags/classifications
- `get_data_quality_results` — fetch test results and incidents

### Webhooks / Events
```bash
# Subscribe to events (table created, test failed, ownership changed)
POST /api/v1/events/subscriptions
{
  "name": "my_webhook",
  "eventType": "POST",
  "filteringRules": { "eventType": ["entityCreated", "testCaseFailed"] },
  "endpoint": "https://my-service.com/webhook"
}
```

---

## 10. Setting Up OpenMetadata Locally

```bash
# Quickstart with Docker Compose
git clone https://github.com/open-metadata/docker-compose.git
cd docker-compose/docker-compose-quickstart
docker compose up -d

# Access
# UI: http://localhost:8585
# API: http://localhost:8585/api/v1
# Default creds: admin / admin

# Connect to MCP
# In Claude Desktop: add to claude_desktop_config.json:
{
  "mcpServers": {
    "openmetadata": {
      "command": "uvx",
      "args": ["mcp-server-openmetadata"],
      "env": {
        "OPENMETADATA_HOST": "http://localhost:8585",
        "OPENMETADATA_JWT_TOKEN": "your-token-here"
      }
    }
  }
}
```

---

## 11. The OpenMetadata Ecosystem

| Tool | Role | OpenMetadata Relationship |
|------|------|--------------------------|
| Apache Airflow | Pipeline orchestration | Native connector, lineage extraction |
| dbt | SQL transformations | Deep integration, column-level lineage |
| Great Expectations | Data quality | Can push test results to OM |
| Apache Spark | Big data processing | Lineage via Spark listener |
| Kafka | Streaming | Topic metadata ingestion |
| Snowflake / BigQuery | Data warehouses | Rich connector with usage stats |
| Tableau / Looker | BI / Dashboards | Dashboard + chart lineage |
| MLflow | ML experiments | ML model metadata |
| GitHub | Code | PRs + code lineage (emerging) |

---

## 12. OpenMetadata vs. Competitors

| Feature | OpenMetadata | DataHub (LinkedIn) | Amundsen (Lyft) | Alation |
|---------|-------------|-------------------|-----------------|---------|
| Open Source | ✅ Fully open | ✅ Mostly open | ✅ | ❌ Proprietary |
| Column-level lineage | ✅ | ✅ | Limited | ✅ |
| Data Quality | ✅ Built-in | Limited | ❌ | ✅ |
| MCP Server | ✅ Native | ❌ | ❌ | ❌ |
| Self-host complexity | Low (4 components) | High (10+ components) | Medium | N/A (SaaS) |
| AI/LLM integration | ✅ First-class | Partial | ❌ | Partial |
| Connectors | 90+ | 70+ | 30+ | 100+ |

**OpenMetadata's unique advantages:** simplest architecture, best MCP/AI integration, built-in data quality, and the most active community momentum right now.

---

## 13. Real Users and Their Pain Points

### Data Engineer ("Priya")
- Pain: "I spend 30% of my time answering questions about table schemas on Slack"
- OM solution: Self-service discovery + documented schemas = fewer interruptions

### Data Analyst ("Rahul")
- Pain: "I don't know if this data is trustworthy or if 'conversion_rate' means what I think it means"
- OM solution: Data quality dashboards + business glossary

### Data Governance Officer ("Sunita")
- Pain: "I need to prove to auditors that all PII is classified and access is controlled"
- OM solution: Auto-classification + RBAC + audit logs

### ML Engineer ("Ankit")
- Pain: "My model's accuracy dropped and I don't know if the training data changed"
- OM solution: Lineage + data quality history

### CTO / VP Engineering
- Pain: "We have a major data incident every month and I don't know why"
- OM solution: Observability + incident tracking + ownership enforcement

---

*This document is your foundation. Read it fully before diving into the project ideas.*
