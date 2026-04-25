import pytest

from agent.schemas.report import BlastRadiusConsumerInput, RCAReport, TimelineEventInput
from app.models import ConfidenceLabel
from om_client.incidents import create_incident


class DummyOMClient:
    def __init__(self, *, post_response, get_responses=None):
        self.post_response = post_response
        self.get_responses = get_responses or {}
        self.last_post_payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def _get(self, path, params=None):
        _ = params
        return self.get_responses.get(path, {"found": False})

    async def _post(self, path, payload):
        _ = path
        self.last_post_payload = payload
        return self.post_response


def _sample_report() -> RCAReport:
    return RCAReport(
        root_cause_summary="Pipeline ingest_orders_daily failed.",
        confidence_score=0.91,
        confidence_label=ConfidenceLabel.HIGH,
        evidence_chain=["Pipeline failure detected"],
        remediation_steps=["Retry pipeline"],
        timeline_events=[
            TimelineEventInput(
                occurred_at="2026-04-22T03:00:00Z",
                event_type="pipeline_failed",
                entity_fqn="airflow.ingest_orders_daily",
                entity_type="pipeline",
                description="Pipeline task failed",
                sequence=1,
            )
        ],
        blast_radius_consumers=[
            BlastRadiusConsumerInput(
                entity_fqn="dbt.default.stg_orders",
                entity_type="table",
                level=1,
                service="dbt",
            )
        ],
        upstream_nodes_checked=3,
        tool_calls_made=4,
        agent_iterations=2,
    )


@pytest.mark.asyncio
async def test_create_incident_success(monkeypatch):
    async def supports():
        return True

    monkeypatch.setattr("om_client.incidents._supports_incidents_api", supports)
    client = DummyOMClient(
        post_response={"id": "om-1"},
        get_responses={
            "/tables/name/mysql.default.raw_orders": {"found": False},
            "/tables/name/mysql.default.default.raw_orders": {
                "found": True,
                "id": "table-1",
            },
        },
    )
    monkeypatch.setattr("om_client.incidents.OMClient", lambda: client)
    result = await create_incident(
        _sample_report(), "mysql.default.raw_orders", "incident-1"
    )
    assert result == "om-1"
    assert client.last_post_payload["entityReference"]["fqn"] == (
        "mysql.default.default.raw_orders"
    )


@pytest.mark.asyncio
async def test_create_incident_not_found(monkeypatch):
    async def supports():
        return True

    monkeypatch.setattr("om_client.incidents._supports_incidents_api", supports)
    client = DummyOMClient(
        post_response={"found": False},
        get_responses={
            "/tables/name/mysql.default.raw_orders": {"found": True, "id": "table-1"},
        },
    )
    monkeypatch.setattr("om_client.incidents.OMClient", lambda: client)
    result = await create_incident(
        _sample_report(), "mysql.default.raw_orders", "incident-1"
    )
    assert result is None


@pytest.mark.asyncio
async def test_create_incident_returns_none_when_table_unresolved(monkeypatch):
    async def supports():
        return True

    monkeypatch.setattr("om_client.incidents._supports_incidents_api", supports)
    client = DummyOMClient(post_response={"id": "om-1"}, get_responses={})
    monkeypatch.setattr("om_client.incidents.OMClient", lambda: client)
    result = await create_incident(
        _sample_report(), "mysql.default.raw_orders", "incident-1"
    )
    assert result is None
    assert client.last_post_payload is None


@pytest.mark.asyncio
async def test_create_incident_returns_none_when_api_not_supported(monkeypatch):
    async def unsupported():
        return False

    monkeypatch.setattr("om_client.incidents._supports_incidents_api", unsupported)
    client = DummyOMClient(post_response={"id": "om-1"}, get_responses={})
    monkeypatch.setattr("om_client.incidents.OMClient", lambda: client)
    result = await create_incident(
        _sample_report(), "mysql.default.raw_orders", "incident-1"
    )
    assert result is None
    assert client.last_post_payload is None
