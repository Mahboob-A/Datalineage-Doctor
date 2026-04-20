from unittest.mock import AsyncMock

import pytest

from agent.tools.pipeline import get_pipeline_entity_status
from om_client.schemas.pipeline import PipelineStatus


@pytest.mark.asyncio
async def test_get_pipeline_entity_status_not_found(monkeypatch):
    monkeypatch.setattr(
        "agent.tools.pipeline.get_pipeline_status",
        AsyncMock(return_value={"found": False}),
    )
    result = await get_pipeline_entity_status("airflow.ingest_orders_daily")
    assert result == {"found": False}


@pytest.mark.asyncio
async def test_get_pipeline_entity_status_success(monkeypatch):
    monkeypatch.setattr(
        "agent.tools.pipeline.get_pipeline_status",
        AsyncMock(
            return_value=PipelineStatus(
                fqn="airflow.ingest_orders_daily",
                last_run_status="Failed",
                last_run_at="2026-04-20T03:00:00+00:00",
                task_statuses=[],
            )
        ),
    )
    result = await get_pipeline_entity_status("airflow.ingest_orders_daily")
    assert result["pipeline_status"]["last_run_status"] == "Failed"
