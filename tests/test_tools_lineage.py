from unittest.mock import AsyncMock

import pytest

from agent.tools.lineage import calculate_blast_radius, get_upstream_lineage
from om_client.schemas.lineage import LineageNode


@pytest.mark.asyncio
async def test_get_upstream_lineage_success(monkeypatch):
    mock = AsyncMock(
        return_value=[
            LineageNode(
                fqn="mysql.default.source_orders",
                entity_type="table",
                service="mysql",
                level=1,
            )
        ]
    )
    monkeypatch.setattr("agent.tools.lineage.om_get_upstream_lineage", mock)

    result = await get_upstream_lineage(table_fqn="mysql.default.raw_orders", depth=2)
    assert len(result["upstream_nodes"]) == 1
    assert result["upstream_nodes"][0]["fqn"] == "mysql.default.source_orders"


@pytest.mark.asyncio
async def test_get_upstream_lineage_error_returns_error_dict(monkeypatch):
    async def _raiser(*args, **kwargs):
        _ = (args, kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr("agent.tools.lineage.om_get_upstream_lineage", _raiser)
    result = await get_upstream_lineage(table_fqn="mysql.default.raw_orders")
    assert result["tool"] == "get_upstream_lineage"


@pytest.mark.asyncio
async def test_calculate_blast_radius_sorts_by_level(monkeypatch):
    mock = AsyncMock(
        return_value=[
            LineageNode(
                fqn="metabase.analytics.orders_dashboard",
                entity_type="dashboard",
                service="metabase",
                level=2,
            ),
            LineageNode(
                fqn="dbt.default.stg_orders",
                entity_type="table",
                service="dbt",
                level=1,
            ),
        ]
    )
    monkeypatch.setattr("agent.tools.lineage.om_get_downstream_lineage", mock)

    result = await calculate_blast_radius(table_fqn="mysql.default.raw_orders", depth=3)
    assert result["total_affected"] == 2
    assert result["blast_radius"][0]["entity_fqn"] == "dbt.default.stg_orders"


@pytest.mark.asyncio
async def test_get_upstream_lineage_accepts_string_depth(monkeypatch):
    captured_depth: list[int] = []

    async def _mock(table_fqn: str, depth: int):
        _ = table_fqn
        captured_depth.append(depth)
        return []

    monkeypatch.setattr("agent.tools.lineage.om_get_upstream_lineage", _mock)

    result = await get_upstream_lineage(
        table_fqn="mysql.default.raw_orders",
        depth="5",  # type: ignore[arg-type]
    )
    assert result["upstream_nodes"] == []
    assert captured_depth == [5]
