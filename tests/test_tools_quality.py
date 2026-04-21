from unittest.mock import AsyncMock

import pytest

from agent.tools.quality import get_dq_test_results
from om_client.schemas.quality import DQTestResult


@pytest.mark.asyncio
async def test_get_dq_test_results_success(monkeypatch):
    mock = AsyncMock(
        return_value=[
            DQTestResult(
                test_case_fqn="mysql.default.raw_orders.row_count_check",
                result="Failed",
                timestamp="2026-04-20T10:00:00+00:00",
                test_type="rowCountToEqual",
            )
        ]
    )
    monkeypatch.setattr("agent.tools.quality.om_get_dq_test_results", mock)

    result = await get_dq_test_results(table_fqn="mysql.default.raw_orders", limit=3)
    assert len(result["test_results"]) == 1
    assert result["test_results"][0]["result"] == "Failed"


@pytest.mark.asyncio
async def test_get_dq_test_results_error(monkeypatch):
    async def _raiser(*args, **kwargs):
        _ = (args, kwargs)
        raise RuntimeError("om error")

    monkeypatch.setattr("agent.tools.quality.om_get_dq_test_results", _raiser)
    result = await get_dq_test_results(table_fqn="mysql.default.raw_orders")
    assert result["tool"] == "get_dq_test_results"


@pytest.mark.asyncio
async def test_get_dq_test_results_accepts_string_limit(monkeypatch):
    captured_limit: list[int] = []

    async def _mock(table_fqn: str, limit: int):
        _ = table_fqn
        captured_limit.append(limit)
        return []

    monkeypatch.setattr("agent.tools.quality.om_get_dq_test_results", _mock)
    result = await get_dq_test_results(
        table_fqn="mysql.default.raw_orders",
        limit="10",  # type: ignore[arg-type]
    )
    assert result["test_results"] == []
    assert captured_limit == [10]
