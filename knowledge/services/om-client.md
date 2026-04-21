# OpenMetadata Client Implementation Guide

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## What This Module Owns

The `om_client/` directory is the single boundary through which the entire project communicates with OpenMetadata. It owns all HTTP requests to the OpenMetadata REST API, JWT authentication, response parsing, error handling, and retry logic. No other module (`app/`, `agent/`, `worker/`) may construct HTTP requests to OpenMetadata directly.

This boundary exists so that OM API changes are always isolated to one place, and so that all OM calls can be mocked at one seam in tests.

---

## Directory Structure

```
om_client/
├── __init__.py
├── client.py           # OMClient class — shared httpx.AsyncClient, auth, base methods
├── lineage.py          # get_upstream_lineage(), get_downstream_lineage()
├── quality.py          # get_dq_test_results()
├── pipeline.py         # get_pipeline_status()
├── ownership.py        # get_entity_owners()
├── incidents.py        # create_incident()
└── schemas/
    ├── __init__.py
    ├── lineage.py      # LineageNode, LineageGraph
    ├── quality.py      # DQTestResult, DQTestSuite
    ├── pipeline.py     # PipelineStatus, TaskStatus
    ├── ownership.py    # EntityOwner
    └── incident.py     # OMIncidentPayload
```

---

## Key Patterns

### Authentication — `client.py`

All requests use a shared `httpx.AsyncClient` instance with a JWT Bearer token set at initialisation. The client is instantiated once per Celery task (not as a module-level singleton) to avoid stale connections across tasks.

```python
import httpx
from app.config import settings

class OMClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=settings.om_base_url,
            headers={
                "Authorization": f"Bearer {settings.om_jwt_token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0),
        )

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
```

Usage pattern in tool functions:

```python
async with OMClient() as om:
    result = await om.get_upstream_lineage(table_fqn, depth=3)
```

### Base Request Method

All API methods go through `_get()` and `_post()` helpers that centralise error handling and retries.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class OMClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(httpx.TransportError),
    )
    async def _get(self, path: str, params: dict | None = None) -> dict:
        response = await self._client.get(path, params=params)

        if response.status_code == 404:
            return {"found": False}

        if response.status_code in (429, 502, 503, 504):
            # tenacity retries on TransportError; raise here to trigger retry
            raise httpx.TransportError(f"Retryable status {response.status_code}")

        response.raise_for_status()
        return response.json()
```

404 responses return `{"found": False}` instead of raising — the agent reasons with partial data rather than crashing on missing entities.

### Lineage Methods — `lineage.py`

```python
async def get_upstream_lineage(
    self, table_fqn: str, depth: int = 3
) -> list[LineageNode]:
    # Resolve table ID from FQN first
    table = await self._get(f"/tables/name/{table_fqn}")
    if not table.get("found", True) or "id" not in table:
        return []

    data = await self._get(
        f"/lineage/table/{table['id']}",
        params={"upstreamDepth": depth, "downstreamDepth": 0},
    )
    return parse_lineage_nodes(data, direction="upstream")


async def get_downstream_lineage(
    self, table_fqn: str, depth: int = 3
) -> list[LineageNode]:
    table = await self._get(f"/tables/name/{table_fqn}")
    if not table.get("found", True) or "id" not in table:
        return []

    data = await self._get(
        f"/lineage/table/{table['id']}",
        params={"upstreamDepth": 0, "downstreamDepth": depth},
    )
    return parse_lineage_nodes(data, direction="downstream")
```

### Response Parsing and Normalisation

Every OM API method returns a normalised Python object, never a raw dict. The caller (agent tool function) always receives typed data.

```python
def parse_lineage_nodes(raw: dict, direction: str) -> list[LineageNode]:
    nodes = raw.get("nodes", [])
    edges = raw.get("edges", [])
    # Build level assignments from edge traversal
    ...
    return [
        LineageNode(
            fqn=node["fullyQualifiedName"],
            entity_type=node["type"].lower(),
            service=extract_service(node),
            level=level_map.get(node["id"], 1),
        )
        for node in nodes
    ]
```

### Error Handling Summary

| Scenario | Behaviour |
|---|---|
| HTTP 404 | Returns `{"found": False}` — not an exception |
| HTTP 429 / 502 / 503 / 504 | Retried up to 3 times with exponential backoff |
| HTTP 400 / 401 / 403 | `raise_for_status()` — propagates as `httpx.HTTPStatusError` |
| Network timeout | `httpx.TimeoutException` — not retried by default; tool returns error dict |
| JSON decode error | Caught, returns `{"error": "invalid_response"}` |

---

## Timeout Strategy

- Default per-request timeout: **30 seconds**
- The OM server can be slow during cold starts; tools use `{"found": False}` gracefully
- The overall LLM timeout (`LLM_TIMEOUT_SECONDS`) provides the outer bound for the full agent loop

---

## Environment Variables

Read via `app.config.settings`:
- `OM_BASE_URL` — e.g. `http://openmetadata_server:8585/api`
- `OM_JWT_TOKEN` — JWT token for all requests
- `OM_MAX_LINEAGE_DEPTH` — default 3; limits depth of lineage traversal calls

---

## Mocking in Tests

In tests, the entire `OMClient` is replaced with a mock. The mock boundary is the `OMClient` class itself.

```python
# In conftest.py
@pytest.fixture
def mock_om_client(mocker):
    mock = AsyncMock(spec=OMClient)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("agent.tools.lineage.OMClient", return_value=mock)
    return mock
```

Tests inject expected return values per method:

```python
mock_om_client.get_upstream_lineage.return_value = [
    LineageNode(fqn="default.raw_orders", entity_type="table", level=1, service="mysql")
]
```

Never call the live OpenMetadata API in tests. See `knowledge/reference/code-examples.md` for the full mocking pattern.
