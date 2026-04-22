import pytest
import respx

from agent.notifications import create_om_incident, notify_slack
from agent.schemas.report import BlastRadiusConsumerInput, RCAReport, TimelineEventInput
from app.config import settings
from app.models import ConfidenceLabel


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
async def test_notify_slack_disabled(monkeypatch):
    monkeypatch.setattr(settings, "slack_enabled", False)
    monkeypatch.setattr(settings, "slack_webhook_url", "")
    result = await notify_slack(_sample_report(), "mysql.default.raw_orders", "id-1")
    assert result is False


@pytest.mark.asyncio
async def test_notify_slack_success(monkeypatch):
    monkeypatch.setattr(settings, "slack_enabled", True)
    monkeypatch.setattr(settings, "slack_webhook_url", "https://hooks.slack.test/abc")
    monkeypatch.setattr(settings, "app_base_url", "http://localhost:8000")

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.post("https://hooks.slack.test/abc").respond(200)
        result = await notify_slack(
            _sample_report(), "mysql.default.raw_orders", "id-1"
        )
    assert result is True


@pytest.mark.asyncio
async def test_create_om_incident_success(monkeypatch):
    async def fake_create(report, table_fqn, incident_id):
        _ = (report, table_fqn, incident_id)
        return "om-123"

    monkeypatch.setattr("agent.notifications.create_incident", fake_create)
    result = await create_om_incident(
        _sample_report(), "mysql.default.raw_orders", "id-1"
    )
    assert result == "om-123"


@pytest.mark.asyncio
async def test_create_om_incident_error(monkeypatch):
    async def fake_create(report, table_fqn, incident_id):
        _ = (report, table_fqn, incident_id)
        raise RuntimeError("boom")

    monkeypatch.setattr("agent.notifications.create_incident", fake_create)
    result = await create_om_incident(
        _sample_report(), "mysql.default.raw_orders", "id-1"
    )
    assert result is None
