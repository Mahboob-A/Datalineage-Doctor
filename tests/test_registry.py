import pytest

from agent.tools.registry import dispatch_tool


@pytest.mark.asyncio
async def test_dispatch_tool_known(monkeypatch):
    async def fake_handler(entity_fqn: str, entity_type: str, db_session):
        _ = (entity_fqn, entity_type, db_session)
        return {"owners": []}

    monkeypatch.setitem(
        dispatch_tool.__globals__["TOOL_HANDLERS"], "get_entity_owners", fake_handler
    )
    result = await dispatch_tool(
        "get_entity_owners",
        {"entity_fqn": "mysql.default.raw_orders", "entity_type": "table"},
        None,
    )
    assert "owners" in result


@pytest.mark.asyncio
async def test_dispatch_tool_unknown():
    result = await dispatch_tool("missing", {}, None)
    assert "error" in result


@pytest.mark.asyncio
async def test_dispatch_tool_handler_exception(monkeypatch):
    async def broken_handler(db_session, **kwargs):
        _ = (db_session, kwargs)
        raise RuntimeError("handler failed")

    monkeypatch.setitem(
        dispatch_tool.__globals__["TOOL_HANDLERS"], "get_entity_owners", broken_handler
    )
    result = await dispatch_tool(
        "get_entity_owners",
        {"entity_fqn": "mysql.default.raw_orders", "entity_type": "table"},
        None,
    )
    assert result["tool"] == "get_entity_owners"


@pytest.mark.asyncio
async def test_dispatch_tool_increments_tool_metric(monkeypatch):
    calls: list[str] = []

    class _Counter:
        def __init__(self, tool_name: str) -> None:
            self.tool_name = tool_name

        def inc(self) -> None:
            calls.append(self.tool_name)

    class _Metric:
        def labels(self, **kwargs):
            return _Counter(kwargs["tool_name"])

    async def fake_handler(entity_fqn: str, entity_type: str, db_session):
        _ = (entity_fqn, entity_type, db_session)
        return {"owners": []}

    monkeypatch.setitem(
        dispatch_tool.__globals__["TOOL_HANDLERS"], "get_entity_owners", fake_handler
    )
    monkeypatch.setitem(dispatch_tool.__globals__, "rca_tool_calls_total", _Metric())

    result = await dispatch_tool(
        "get_entity_owners",
        {"entity_fqn": "mysql.default.raw_orders", "entity_type": "table"},
        None,
    )
    assert "owners" in result
    assert calls == ["get_entity_owners"]
