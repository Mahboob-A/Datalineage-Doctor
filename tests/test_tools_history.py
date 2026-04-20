from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agent.tools.history import find_past_incidents
from app.models import ConfidenceLabel


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalarResult(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, statement):
        _ = statement
        return _FakeExecuteResult(self._rows)


@pytest.mark.asyncio
async def test_find_past_incidents_without_session():
    result = await find_past_incidents(
        table_fqn="mysql.default.raw_orders", db_session=None
    )
    assert result == {"past_incidents": [], "count": 0}


@pytest.mark.asyncio
async def test_find_past_incidents_success():
    rows = [
        SimpleNamespace(
            id=uuid4(),
            triggered_at=datetime(2026, 4, 20, 10, 0, tzinfo=UTC),
            root_cause_summary="Pipeline failed",
            confidence_label=ConfidenceLabel.HIGH,
        ),
        SimpleNamespace(
            id=uuid4(),
            triggered_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC),
            root_cause_summary="Schema drift",
            confidence_label=ConfidenceLabel.MEDIUM,
        ),
    ]
    session = _FakeSession(rows)

    result = await find_past_incidents(
        table_fqn="mysql.default.raw_orders",
        db_session=session,
    )

    assert result["count"] == 2
    assert result["past_incidents"][0]["confidence_label"] == "HIGH"
