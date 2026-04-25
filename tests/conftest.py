import os
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("OM_JWT_TOKEN", "test-token")

from app.main import app  # noqa: E402
from app.models.incident import ConfidenceLabel, IncidentStatus  # noqa: E402


def _now():
    return datetime(2026, 4, 22, 3, 0, tzinfo=timezone.utc)


@dataclass
class MockIncident:
    """A mock incident that mimics the SQLAlchemy model for template rendering."""
    id: str
    table_fqn: str
    test_case_fqn: str
    triggered_at: datetime
    status: IncidentStatus
    confidence_label: ConfidenceLabel
    confidence_score: float
    evidence_chain: list[str]
    remediation_steps: list[str]
    blast_radius_count: int
    root_cause_summary: str | None


@dataclass
class MockTimeline:
    occurred_at: datetime
    event_type: str
    entity_fqn: str
    entity_type: str
    description: str
    sequence: int


@dataclass
class MockBlastRadius:
    entity_fqn: str
    entity_type: str
    level: int
    service: str


@pytest.fixture
def mock_list_incidents_result():
    """Sample incidents for mock list."""
    return [
        MockIncident(
            id="123",
            table_fqn="mysql.default.raw_orders",
            test_case_fqn="null_check_order_id",
            triggered_at=_now(),
            status=IncidentStatus.COMPLETE,
            confidence_label=ConfidenceLabel.HIGH,
            confidence_score=0.9,
            evidence_chain=["evidence"],
            remediation_steps=["step"],
            blast_radius_count=3,
            root_cause_summary="pipeline failed",
        )
    ]


@pytest.fixture
def mock_detail_result():
    """Sample detail data for mock detail endpoint."""
    incident = MockIncident(
        id="123",
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="null_check_order_id",
        triggered_at=_now(),
        status=IncidentStatus.COMPLETE,
        confidence_label=ConfidenceLabel.HIGH,
        confidence_score=0.9,
        evidence_chain=["evidence"],
        remediation_steps=["step"],
        blast_radius_count=1,
        root_cause_summary="pipeline failed",
    )
    timeline = [
        MockTimeline(
            occurred_at=_now(),
            event_type="pipeline_failed",
            entity_fqn="airflow.ingest_orders_daily",
            entity_type="pipeline",
            description="failed",
            sequence=1,
        )
    ]
    blast = [
        MockBlastRadius(
            entity_fqn="dbt.default.stg_orders",
            entity_type="table",
            level=1,
            service="dbt",
        )
    ]
    return incident, timeline, blast


@pytest.fixture
def client(mock_list_incidents_result, mock_detail_result):
    """Create a test client with mocked incident store functions."""
    async def mock_list(db, page=1, page_size=20):
        return mock_list_incidents_result
    
    async def mock_detail(db, incident_id):
        if incident_id == "00000000-0000-0000-0000-000000000123":
            return mock_detail_result
        return None
    
    # Patch at the dashboard router level where the functions are used
    with patch("app.routers.dashboard.list_incidents", mock_list):
        with patch("app.routers.dashboard.get_incident_detail", mock_detail):
            yield TestClient(app)
