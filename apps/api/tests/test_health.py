from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_ready_endpoint_reports_local_configuration() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "configured"
    assert payload["redis"] == "configured"


def test_metrics_endpoint_exposes_prometheus_metrics() -> None:
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "http_requests_total" in body
    assert 'path="/health"' in body
    assert "llm_gateway_rate_limit_rejections_total" in body
