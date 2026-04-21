# API Specification

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## API Conventions

- All endpoints return `application/json` except dashboard routes which return `text/html`
- Timestamps are ISO 8601 with UTC timezone: `2026-04-17T10:30:00Z`
- UUIDs are lowercase hyphenated strings: `"3fa85f64-5717-4562-b3fc-2c963f66afa6"`
- Error responses always include `"error"` and `"detail"` keys
- Pagination uses `page` (1-indexed) and `page_size` query parameters
- The API has no versioning prefix in MVP — all routes are at root `/`

---

## Authentication

No authentication is required on any endpoint in MVP. The app runs on a local Docker network only. Webhook signature verification is `[FUTURE]` scope.

---

## Endpoints

---

### POST `/webhook/openmetadata`

Receives OpenMetadata event payloads. Returns immediately; processing is asynchronous.

**Auth required:** No

**Request headers:**
```
Content-Type: application/json
```

**Request body:**
```json
{
  "eventType": "testCaseFailed",
  "entityType": "testCase",
  "timestamp": 1713340200000,
  "entity": {
    "id": "abc123",
    "name": "null_check_order_id",
    "fullyQualifiedName": "mysql.default.raw_orders.null_check_order_id",
    "entityType": "testCase"
  },
  "changeDescription": {
    "fieldsUpdated": [
      {
        "name": "testCaseResult",
        "newValue": "Failed",
        "oldValue": "Success"
      }
    ]
  }
}
```

**Field notes:**
- `eventType` — required. Only `testCaseFailed` is processed; all other values are silently accepted and ignored.
- `entity.fullyQualifiedName` — used to extract the table FQN (everything up to the test case name segment).
- `timestamp` — Unix milliseconds. Converted to ISO 8601 internally.

**Response — 202 Accepted (event queued):**
```json
{
  "status": "queued",
  "task_id": "3b2c1a0d-9e8f-7a6b-5c4d-3e2f1a0b9c8d"
}
```

**Response — 202 Accepted (event ignored):**
```json
{
  "status": "ignored"
}
```

**Response — 400 Bad Request (validation failure):**
```json
{
  "error": "validation_error",
  "detail": [
    {
      "loc": ["body", "eventType"],
      "msg": "field required",
      "type": "missing"
    }
  ]
}
```

**Error codes:**

| Status | Condition |
|---|---|
| 202 | Valid payload — queued or ignored |
| 400 | Missing required fields or invalid JSON |
| 422 | Pydantic validation failure (type mismatch) |
| 500 | Unexpected server error |

---

### GET `/`

Renders the incidents list dashboard page (HTML).

**Auth required:** No

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number (1-indexed) |
| `page_size` | integer | 20 | Items per page (max 100) |

**Response — 200 OK:** Jinja2-rendered HTML page.

The page displays a table of incidents ordered by `triggered_at` descending. Each row includes:
- Table FQN
- Triggered at (human-readable)
- Status badge (`processing` / `complete` / `failed`)
- Confidence label badge (`HIGH` / `MEDIUM` / `LOW`)
- Blast radius count
- Link to detail page

**Error codes:**

| Status | Condition |
|---|---|
| 200 | Page rendered successfully |
| 500 | Database error |

---

### GET `/incidents/{id}`

Renders the incident detail dashboard page (HTML).

**Auth required:** No

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID string | Incident ID |

**Response — 200 OK:** Jinja2-rendered HTML page.

The page includes:
- Incident summary header (table FQN, triggered at, status, confidence badge)
- Root cause narrative
- Confidence score and label
- Evidence chain (ordered list)
- Remediation steps (ordered list)
- React Flow lineage graph (loaded from CDN, graph data injected as JSON in a `<script>` tag)
- Chronological timeline of events
- Blast radius consumer table

**React Flow graph data shape (injected into template):**
```json
{
  "nodes": [
    {
      "id": "mysql.default.raw_orders",
      "data": { "label": "raw_orders", "service": "mysql", "is_root_cause": true },
      "type": "custom",
      "position": { "x": 0, "y": 0 }
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "mysql.default.raw_orders",
      "target": "dbt.default.stg_orders"
    }
  ]
}
```

`is_root_cause: true` causes the node to render with a red border in the React Flow custom node component.

**Response — 404 Not Found:**
```json
{
  "error": "not_found",
  "detail": "Incident 3fa85f64-... not found"
}
```

**Error codes:**

| Status | Condition |
|---|---|
| 200 | Incident found and rendered |
| 404 | Incident ID does not exist |
| 422 | ID is not a valid UUID format |
| 500 | Database error |

---

### GET `/health`

Health check endpoint. Used by Docker Compose `healthcheck` and monitoring.

**Auth required:** No

**Response — 200 OK:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "env": "development"
}
```

**Response — 503 Service Unavailable** (if database is unreachable):
```json
{
  "status": "degraded",
  "checks": {
    "database": "unreachable"
  }
}
```

---

### GET `/metrics`

Prometheus metrics endpoint. Returns metrics in Prometheus text format.

**Auth required:** No

**Response — 200 OK:**
```
# HELP rca_requests_total Total number of RCA tasks received
# TYPE rca_requests_total counter
rca_requests_total{status="success"} 12.0
rca_requests_total{status="failure"} 1.0

# HELP rca_duration_seconds Time taken to complete an RCA run
# TYPE rca_duration_seconds histogram
rca_duration_seconds_bucket{le="30.0"} 2.0
rca_duration_seconds_bucket{le="60.0"} 7.0
rca_duration_seconds_bucket{le="120.0"} 12.0
rca_duration_seconds_bucket{le="+Inf"} 13.0
rca_duration_seconds_sum 756.4
rca_duration_seconds_count 13.0

# HELP rca_tool_calls_total Total tool calls by tool name
# TYPE rca_tool_calls_total counter
rca_tool_calls_total{tool_name="get_upstream_lineage"} 24.0
rca_tool_calls_total{tool_name="get_dq_test_results"} 18.0
rca_tool_calls_total{tool_name="calculate_blast_radius"} 13.0

# HELP rca_confidence_score Confidence score of the most recent RCA run
# TYPE rca_confidence_score gauge
rca_confidence_score 0.91

# HELP blast_radius_size Number of downstream consumers per incident
# TYPE blast_radius_size histogram
blast_radius_size_bucket{le="5.0"} 8.0
blast_radius_size_bucket{le="10.0"} 12.0
blast_radius_size_bucket{le="+Inf"} 13.0

# HELP rca_errors_total Total errors by error type
# TYPE rca_errors_total counter
rca_errors_total{error_type="llm_timeout"} 0.0
rca_errors_total{error_type="om_api_error"} 2.0
```

**Content-Type:** `text/plain; version=0.0.4; charset=utf-8`

---

## Error Response Format

All non-HTML error responses use this shape:

```json
{
  "error": "error_code_snake_case",
  "detail": "Human-readable explanation or structured validation errors"
}
```

Common error codes:

| Code | HTTP status | Meaning |
|---|---|---|
| `validation_error` | 400 | Request body failed schema validation |
| `not_found` | 404 | Requested resource does not exist |
| `internal_error` | 500 | Unhandled server error |

---

## Validation Rules

- `POST /webhook/openmetadata` — `eventType`, `entityType`, `entity`, `entity.fullyQualifiedName` are required
- `GET /incidents/{id}` — `id` must be a valid UUID v4 string
- `GET /` — `page` must be ≥ 1; `page_size` must be between 1 and 100
