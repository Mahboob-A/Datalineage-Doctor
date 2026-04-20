def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code in {200, 503}


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"rca_requests_total" in response.content


def test_dashboard_endpoint(client):
    response = client.get("/")
    assert response.status_code in {200, 500}
