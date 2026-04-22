import pytest

from agent.schemas.report import BlastRadiusConsumerInput, RCAReport, TimelineEventInput
from app.models import ConfidenceLabel
from om_client.incidents import create_incident


class DummyOMClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def _post(self, path, payload):
        _ = (path, payload)
        return self.response


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
    monkeypatch.setattr(
        "om_client.incidents.OMClient", lambda: DummyOMClient({"id": "om-1"})
    )
    result = await create_incident(
        _sample_report(), "mysql.default.raw_orders", "incident-1"
    )
    assert result == "om-1"


@pytest.mark.asyncio
async def test_create_incident_not_found(monkeypatch):
    monkeypatch.setattr(
        "om_client.incidents.OMClient", lambda: DummyOMClient({"found": False})
    )
    result = await create_incident(
        _sample_report(), "mysql.default.raw_orders", "incident-1"
    )
    assert result is None
