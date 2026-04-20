import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from agent.loop import run_rca_agent
from app.models import ConfidenceLabel


def _report_content(
    confidence_score: float = 0.9, confidence_label: str = "LOW"
) -> str:
    return json.dumps(
        {
            "root_cause_summary": "Pipeline failure caused stale data.",
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "evidence_chain": ["Evidence 1", "Evidence 2", "Evidence 3"],
            "remediation_steps": ["Fix pipeline", "Backfill affected table"],
            "timeline_events": [
                {
                    "occurred_at": "2026-04-20T10:00:00+00:00",
                    "event_type": "pipeline_failure",
                    "entity_fqn": "airflow.ingest_orders_daily",
                    "entity_type": "pipeline",
                    "description": "Pipeline run failed.",
                    "sequence": 1,
                }
            ],
            "blast_radius_consumers": [],
            "upstream_nodes_checked": 2,
            "tool_calls_made": 0,
            "agent_iterations": 1,
        }
    )


def _stop_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=content, tool_calls=[]),
            )
        ]
    )


def _tool_call_response(
    name: str, args: dict[str, object], call_id: str = "call-1"
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason="tool_calls",
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id=call_id,
                            function=SimpleNamespace(
                                name=name, arguments=json.dumps(args)
                            ),
                        )
                    ],
                ),
            )
        ]
    )


@pytest.mark.asyncio
async def test_run_rca_agent_stop_parses_report(monkeypatch):
    async def fake_call_llm(*, client, messages):
        _ = (client, messages)
        return _stop_response(
            _report_content(confidence_score=0.91, confidence_label="LOW")
        )

    monkeypatch.setattr("agent.loop.call_llm", fake_call_llm)
    report = await run_rca_agent(
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="orders_row_count_check",
        triggered_at="2026-04-20T10:00:00+00:00",
        db_session=None,
    )
    assert report.root_cause_summary == "Pipeline failure caused stale data."
    assert report.confidence_label == ConfidenceLabel.HIGH


@pytest.mark.asyncio
async def test_run_rca_agent_tool_calls_then_stop(monkeypatch):
    call_sequence = [
        _tool_call_response(
            "get_upstream_lineage", {"table_fqn": "mysql.default.raw_orders"}
        ),
        _stop_response(_report_content(confidence_score=0.88, confidence_label="LOW")),
    ]
    called_tools: list[str] = []

    async def fake_call_llm(*, client, messages):
        _ = (client, messages)
        return call_sequence.pop(0)

    async def fake_dispatch_tool(tool_name: str, args: dict, db_session):
        _ = (args, db_session)
        called_tools.append(tool_name)
        return {"upstream_nodes": []}

    monkeypatch.setattr("agent.loop.call_llm", fake_call_llm)
    monkeypatch.setattr("agent.loop.dispatch_tool", fake_dispatch_tool)

    report = await run_rca_agent(
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="orders_row_count_check",
        triggered_at="2026-04-20T10:00:00+00:00",
        db_session=None,
    )

    assert called_tools == ["get_upstream_lineage"]
    assert report.tool_calls_made == 1


@pytest.mark.asyncio
async def test_run_rca_agent_max_iterations_returns_fallback(monkeypatch):
    async def fake_call_llm(*, client, messages):
        _ = (client, messages)
        return _tool_call_response(
            "get_upstream_lineage", {"table_fqn": "mysql.default.raw_orders"}
        )

    async def fake_dispatch_tool(tool_name: str, args: dict, db_session):
        _ = (tool_name, args, db_session)
        return {"upstream_nodes": []}

    monkeypatch.setattr("agent.loop.call_llm", fake_call_llm)
    monkeypatch.setattr("agent.loop.dispatch_tool", fake_dispatch_tool)
    monkeypatch.setattr("agent.loop.settings.llm_max_iterations", 2)

    report = await run_rca_agent(
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="orders_row_count_check",
        triggered_at="2026-04-20T10:00:00+00:00",
        db_session=None,
    )

    assert report.confidence_label == ConfidenceLabel.LOW
    assert report.agent_iterations == 2


@pytest.mark.asyncio
async def test_run_rca_agent_passes_incident_id_to_tool_log(monkeypatch):
    call_sequence = [
        _tool_call_response(
            "get_upstream_lineage", {"table_fqn": "mysql.default.raw_orders"}
        ),
        _stop_response(_report_content(confidence_score=0.88, confidence_label="LOW")),
    ]
    captured_incident_ids: list[UUID | None] = []

    async def fake_call_llm(*, client, messages):
        _ = (client, messages)
        return call_sequence.pop(0)

    async def fake_dispatch_tool(tool_name: str, args: dict, db_session):
        _ = (tool_name, args, db_session)
        return {"upstream_nodes": []}

    async def fake_log_tool_call(
        *,
        incident_id,
        tool_name,
        input_args,
        result,
        duration_ms,
        success,
        error_message,
        iteration,
        db_session,
    ):
        _ = (
            tool_name,
            input_args,
            result,
            duration_ms,
            success,
            error_message,
            iteration,
            db_session,
        )
        captured_incident_ids.append(incident_id)

    monkeypatch.setattr("agent.loop.call_llm", fake_call_llm)
    monkeypatch.setattr("agent.loop.dispatch_tool", fake_dispatch_tool)
    monkeypatch.setattr("agent.loop.log_tool_call", fake_log_tool_call)

    expected_incident_id = UUID("099be50e-bdcf-4610-9199-b76572bea99a")
    report = await run_rca_agent(
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="orders_row_count_check",
        triggered_at="2026-04-20T10:00:00+00:00",
        db_session=None,
        incident_id=expected_incident_id,
    )

    assert report.tool_calls_made == 1
    assert captured_incident_ids == [expected_incident_id]
