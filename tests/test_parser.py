import json

import pytest

from agent.parser import RCAParseError, derive_confidence_label, parse_rca_report
from app.models import ConfidenceLabel


def _valid_report_json(confidence_score: float, confidence_label: str) -> str:
    return json.dumps(
        {
            "root_cause_summary": "Pipeline failure caused stale data.",
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "evidence_chain": ["Evidence 1", "Evidence 2", "Evidence 3"],
            "remediation_steps": ["Fix pipeline"],
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
            "tool_calls_made": 1,
            "agent_iterations": 1,
        }
    )


def test_parse_rca_report_recalculates_confidence_label() -> None:
    content = _valid_report_json(confidence_score=0.90, confidence_label="LOW")
    report = parse_rca_report(content)
    assert report.confidence_label == ConfidenceLabel.HIGH


def test_parse_rca_report_supports_markdown_fence() -> None:
    content = f"```json\n{_valid_report_json(confidence_score=0.72, confidence_label='HIGH')}\n```"
    report = parse_rca_report(content)
    assert report.confidence_label == ConfidenceLabel.MEDIUM


def test_parse_rca_report_raises_on_invalid_json() -> None:
    with pytest.raises(RCAParseError):
        parse_rca_report("not valid json")


@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (0.20, ConfidenceLabel.LOW),
        (0.60, ConfidenceLabel.MEDIUM),
        (0.85, ConfidenceLabel.HIGH),
    ],
)
def test_derive_confidence_label(score: float, expected_label: ConfidenceLabel) -> None:
    assert derive_confidence_label(score) == expected_label
