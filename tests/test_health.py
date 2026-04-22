def test_health_endpoint(client):
    """Test health endpoint returns expected status."""
    response = client.get("/health")
    assert response.status_code in {200, 503}


def test_metrics_endpoint(client):
    """Test metrics endpoint returns Prometheus metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"rca_requests_total" in response.content
