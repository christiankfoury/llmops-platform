import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.main import app
from scripts.seed_dev_data import PLACEHOLDER_API_KEY, main as seed_dev_data


client = TestClient(app)


def _database_available() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
        return True
    except SQLAlchemyError:
        return False


requires_database = pytest.mark.skipif(
    not _database_available(),
    reason="local PostgreSQL is not available",
)


@requires_database
def test_gateway_completion_persists_successful_request() -> None:
    seed_dev_data()

    response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "hello from the gateway test"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["provider"] == "mock"
    assert payload["model"] == "mock-llm-small"
    assert payload["request_id"].startswith("req_")
    assert payload["latency_ms"] >= 1
    assert payload["input_tokens"] >= 1
    assert payload["output_tokens"] >= 1

    with SessionLocal() as db:
        persisted = db.execute(
            text(
                "select status, latency_ms, estimated_cost_usd "
                "from gateway_requests "
                "where request_id = :request_id"
            ),
            {"request_id": payload["request_id"]},
        ).one()

    assert persisted.status == "succeeded"
    assert persisted.latency_ms >= 1
    assert persisted.estimated_cost_usd is not None


@requires_database
def test_gateway_rejects_invalid_api_key() -> None:
    seed_dev_data()

    response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": "not-a-valid-placeholder"},
        json={"input": "this should not be accepted"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


@requires_database
def test_gateway_records_provider_failure() -> None:
    seed_dev_data()

    response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "[simulate_failure]"},
    )

    assert response.status_code == 502

    with SessionLocal() as db:
        latest_failure = db.execute(
            text(
                "select status, error_category, latency_ms "
                "from gateway_requests "
                "where error_category = 'provider_error' "
                "order by created_at desc "
                "limit 1"
            )
        ).one()

    assert latest_failure.status == "failed"
    assert latest_failure.error_category == "provider_error"
    assert latest_failure.latency_ms >= 1


@requires_database
def test_usage_summary_returns_request_count_and_cost() -> None:
    seed_dev_data()
    client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "usage summary test"},
    )

    response = client.get("/v1/usage/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_count"] >= 1
    assert payload["average_latency_ms"] >= 1
    assert "estimated_cost_usd" in payload
