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
