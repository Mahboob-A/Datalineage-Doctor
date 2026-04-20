from unittest.mock import AsyncMock

import pytest

from agent.tools.ownership import get_entity_owners
from om_client.schemas.ownership import EntityOwner


@pytest.mark.asyncio
async def test_get_entity_owners_success(monkeypatch):
    monkeypatch.setattr(
        "agent.tools.ownership.om_get_entity_owners",
        AsyncMock(
            return_value=[
                EntityOwner(name="Data Team", email="data@example.com", type="team")
            ]
        ),
    )
    result = await get_entity_owners("mysql.default.raw_orders", "table")
    assert len(result["owners"]) == 1
    assert result["owners"][0]["type"] == "team"


@pytest.mark.asyncio
async def test_get_entity_owners_error(monkeypatch):
    async def _raiser(*args, **kwargs):
        _ = (args, kwargs)
        raise RuntimeError("om failed")

    monkeypatch.setattr("agent.tools.ownership.om_get_entity_owners", _raiser)
    result = await get_entity_owners("mysql.default.raw_orders", "table")
    assert result["tool"] == "get_entity_owners"
