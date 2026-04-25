"""Dashboard route rendering tests (with mocked DB access)."""


def test_dashboard_list_renders(client):
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "mysql.default.raw_orders" in response.text


def test_dashboard_detail_renders(client):
    response = client.get(
        "/incidents/00000000-0000-0000-0000-000000000123",
        headers={"accept": "text/html"},
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "mysql.default.raw_orders" in response.text


def test_dashboard_detail_404(client):
    response = client.get(
        "/incidents/00000000-0000-0000-0000-000000000000",
        headers={"accept": "text/html"},
    )
    assert response.status_code == 404


def test_latest_incident_api(client):
    response = client.get("/api/incidents/latest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["table_fqn"] == "mysql.default.raw_orders"


def test_latest_incident_api_not_found(client, monkeypatch):
    async def _missing_incident(db):
        _ = db
        return None

    monkeypatch.setattr("app.routers.dashboard.latest_incident", _missing_incident)
    response = client.get("/api/incidents/latest")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
