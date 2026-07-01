import json
import logging

from app.config import get_settings
from app.main import app
from app.observability.logging import CorrelationJsonFormatter
from fastapi.testclient import TestClient

client = TestClient(app)


def test_request_id_header_is_propagated() -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-id"


def test_tracing_is_disabled_by_default() -> None:
    settings = get_settings()

    assert settings.otel_tracing_enabled is False
    assert settings.otel_service_name == "production-ai-platform-api"


def test_json_logs_honor_explicit_correlation_fields() -> None:
    record = logging.LogRecord(
        name="app.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-test"
    record.trace_id = "0123456789abcdef0123456789abcdef"
    record.status_code = 200

    payload = json.loads(CorrelationJsonFormatter().format(record))

    assert payload["request_id"] == "req-test"
    assert payload["trace_id"] == "0123456789abcdef0123456789abcdef"
    assert payload["status_code"] == 200
