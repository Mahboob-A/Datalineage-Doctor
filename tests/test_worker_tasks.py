import pytest

from worker import tasks


class _Counter:
    def __init__(self, sink: list[tuple[str, str]], key: str, value: str) -> None:
        self._sink = sink
        self._key = key
        self._value = value

    def inc(self) -> None:
        self._sink.append((self._key, self._value))


class _LabelMetric:
    def __init__(self, sink: list[tuple[str, str]], key: str) -> None:
        self._sink = sink
        self._key = key

    def labels(self, **kwargs):
        value = kwargs[self._key]
        return _Counter(self._sink, self._key, value)


class _ObserveMetric:
    def __init__(self) -> None:
        self.values: list[float] = []

    def observe(self, value: float) -> None:
        self.values.append(value)


class _SetMetric:
    def __init__(self) -> None:
        self.values: list[float] = []

    def set(self, value: float) -> None:
        self.values.append(value)


@pytest.mark.asyncio
async def test_run_updates_confidence_and_blast_metrics(monkeypatch):
    confidence_metric = _SetMetric()
    blast_metric = _ObserveMetric()

    class _Report:
        confidence_score = 0.91
        blast_radius_consumers = [{"entity_fqn": "dbt.default.stg_orders"}]

    async def fake_save_incident(*args, **kwargs):
        _ = args
        if kwargs.get("incident_id") is None:
            return "incident-1"
        return "incident-1"

    async def fake_run_rca_agent(*args, **kwargs):
        _ = (args, kwargs)
        return _Report()

    async def fake_notify_slack(*args, **kwargs):
        _ = (args, kwargs)
        return False

    async def fake_create_om_incident(*args, **kwargs):
        _ = (args, kwargs)
        return None

    monkeypatch.setattr("worker.tasks.save_incident", fake_save_incident)
    monkeypatch.setattr("worker.tasks.run_rca_agent", fake_run_rca_agent)
    monkeypatch.setattr("worker.tasks.notify_slack", fake_notify_slack)
    monkeypatch.setattr("worker.tasks.create_om_incident", fake_create_om_incident)
    monkeypatch.setattr("worker.tasks.rca_confidence_score", confidence_metric)
    monkeypatch.setattr("worker.tasks.blast_radius_size", blast_metric)

    result = await tasks._run(
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="orders_row_count_check",
        triggered_at="2026-04-25T10:00:00+00:00",
    )

    assert result["status"] == "complete"
    assert confidence_metric.values == [0.91]
    assert blast_metric.values == [1.0]


def test_rca_task_increments_success_and_duration(monkeypatch):
    request_calls: list[tuple[str, str]] = []
    error_calls: list[tuple[str, str]] = []
    duration_metric = _ObserveMetric()

    async def fake_run(*args, **kwargs):
        _ = (args, kwargs)
        return {"status": "complete", "incident_id": "abc"}

    monkeypatch.setattr("worker.tasks._run", fake_run)
    monkeypatch.setattr(
        "worker.tasks.rca_requests_total", _LabelMetric(request_calls, "status")
    )
    monkeypatch.setattr(
        "worker.tasks.rca_errors_total", _LabelMetric(error_calls, "error_type")
    )
    monkeypatch.setattr("worker.tasks.rca_duration_seconds", duration_metric)

    result = tasks.rca_task.run(
        table_fqn="mysql.default.raw_orders",
        test_case_fqn="orders_row_count_check",
        triggered_at="2026-04-25T10:00:00+00:00",
    )

    assert result["status"] == "complete"
    assert request_calls == [("status", "success")]
    assert error_calls == []
    assert len(duration_metric.values) == 1


def test_rca_task_increments_failure_and_error_counter(monkeypatch):
    request_calls: list[tuple[str, str]] = []
    error_calls: list[tuple[str, str]] = []
    duration_metric = _ObserveMetric()

    async def fake_run(*args, **kwargs):
        _ = (args, kwargs)
        raise RuntimeError("task failed")

    monkeypatch.setattr("worker.tasks._run", fake_run)
    monkeypatch.setattr(
        "worker.tasks.rca_requests_total", _LabelMetric(request_calls, "status")
    )
    monkeypatch.setattr(
        "worker.tasks.rca_errors_total", _LabelMetric(error_calls, "error_type")
    )
    monkeypatch.setattr("worker.tasks.rca_duration_seconds", duration_metric)

    with pytest.raises(RuntimeError, match="task failed"):
        tasks.rca_task.run(
            table_fqn="mysql.default.raw_orders",
            test_case_fqn="orders_row_count_check",
            triggered_at="2026-04-25T10:00:00+00:00",
        )

    assert request_calls == [("status", "failure")]
    assert error_calls == [("error_type", "task_failure")]
    assert len(duration_metric.values) == 1
