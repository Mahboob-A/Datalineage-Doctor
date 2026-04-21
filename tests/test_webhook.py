from datetime import UTC, datetime


def _valid_payload() -> dict:
    return {
        "eventType": "testCaseFailed",
        "entityType": "testCase",
        "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
        "entity": {
            "id": "id-1",
            "name": "orders_count_check",
            "fullyQualifiedName": "mysql.default.raw_orders",
            "entityType": "table",
        },
    }


def test_webhook_queued(client, monkeypatch):
    class _Task:
        id = "task-123"

    class _Counter:
        def inc(self):
            return None

    class _Metric:
        def labels(self, **kwargs):
            _ = kwargs
            return _Counter()

    monkeypatch.setattr("app.routers.webhook.rca_task.delay", lambda **_: _Task())
    monkeypatch.setattr("app.routers.webhook.rca_requests_total", _Metric())
    response = client.post("/webhook/openmetadata", json=_valid_payload())
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_webhook_ignored(client, monkeypatch):
    class _Counter:
        def inc(self):
            return None

    class _Metric:
        def labels(self, **kwargs):
            _ = kwargs
            return _Counter()

    monkeypatch.setattr("app.routers.webhook.rca_requests_total", _Metric())
    payload = _valid_payload()
    payload["eventType"] = "tableUpdated"
    response = client.post("/webhook/openmetadata", json=payload)
    assert response.status_code == 202
    assert response.json() == {"status": "ignored", "task_id": None}


def test_webhook_missing_entity(client):
    payload = _valid_payload()
    payload.pop("entity")
    response = client.post("/webhook/openmetadata", json=payload)
    assert response.status_code == 422


def test_webhook_wrong_content_type(client):
    response = client.post("/webhook/openmetadata", data="x")
    assert response.status_code in {400, 415, 422}
