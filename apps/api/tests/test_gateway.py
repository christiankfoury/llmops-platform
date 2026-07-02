from decimal import Decimal

import pytest
from app.db.session import SessionLocal
from app.main import app
from fastapi.testclient import TestClient
from scripts.seed_dev_data import PLACEHOLDER_API_KEY
from scripts.seed_dev_data import main as seed_dev_data
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

client = TestClient(app)


def _demo_scope() -> tuple[dict, dict]:
    scopes_response = client.get("/v1/usage/scopes")
    assert scopes_response.status_code == 200
    project = next(project for project in scopes_response.json() if project["slug"] == "demo-project")
    application = next(
        application
        for application in project["applications"]
        if application["slug"] == "demo-app"
    )
    return project, application


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

    metrics_response = client.get("/metrics")
    assert "llm_gateway_requests_total" in metrics_response.text
    assert "llm_gateway_estimated_cost_usd_total" in metrics_response.text
    assert "llm_gateway_tokens_total" in metrics_response.text

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

    metrics_response = client.get("/metrics")
    assert "llm_gateway_api_key_auth_failures_total" in metrics_response.text


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
def test_gateway_retries_transient_provider_failure() -> None:
    seed_dev_data()

    response = client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "[simulate_transient_failure]"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"

    with SessionLocal() as db:
        persisted = db.execute(
            text(
                "select status, error_category from gateway_requests where request_id = :request_id"
            ),
            {"request_id": payload["request_id"]},
        ).one()

    assert persisted.status == "succeeded"
    assert persisted.error_category is None


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


@requires_database
def test_usage_summary_respects_scope_status_model_and_date_filters() -> None:
    seed_dev_data()
    client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "usage filter success"},
    )
    client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "[simulate_failure]"},
    )

    project, application = _demo_scope()

    success_response = client.get(
        "/v1/usage/summary",
        params={
            "project_id": project["id"],
            "application_id": application["id"],
            "status": "succeeded",
            "provider": "mock",
            "model_name": "mock-llm-small",
        },
    )
    future_response = client.get(
        "/v1/usage/summary",
        params={"created_from": "2999-01-01T00:00:00Z", "model_name": "mock-llm-small"},
    )

    assert success_response.status_code == 200
    success_payload = success_response.json()
    assert success_payload["request_count"] >= 1
    assert success_payload["error_count"] == 0
    assert Decimal(success_payload["estimated_cost_usd"]) > Decimal("0")

    assert future_response.status_code == 200
    future_payload = future_response.json()
    assert future_payload["request_count"] == 0
    assert future_payload["estimated_cost_usd"] == "0.000000"


@requires_database
def test_usage_request_lists_return_recent_records() -> None:
    seed_dev_data()
    client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "request list test"},
    )
    client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "[simulate_failure]"},
    )

    requests_response = client.get("/v1/usage/requests?limit=5")
    errors_response = client.get("/v1/usage/errors?limit=5")

    assert requests_response.status_code == 200
    assert errors_response.status_code == 200
    assert len(requests_response.json()) >= 1
    assert any(record["status"] == "failed" for record in errors_response.json())


@requires_database
def test_usage_request_filters_include_scope_labels_and_cap_limit() -> None:
    seed_dev_data()
    client.post(
        "/v1/gateway/completions",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json={"input": "[simulate_failure]"},
    )

    project, application = _demo_scope()

    requests_response = client.get(
        "/v1/usage/requests",
        params={
            "project_id": project["id"],
            "application_id": application["id"],
            "status": "failed",
            "error_category": "provider_error",
            "limit": 500,
        },
    )
    errors_response = client.get(
        "/v1/usage/errors",
        params={
            "project_id": project["id"],
            "application_id": application["id"],
            "error_category": "provider_error",
            "limit": 500,
        },
    )

    assert requests_response.status_code == 200
    assert errors_response.status_code == 200
    request_records = requests_response.json()
    error_records = errors_response.json()
    assert 1 <= len(request_records) <= 100
    assert 1 <= len(error_records) <= 100
    assert all(record["status"] == "failed" for record in request_records)
    latest = request_records[0]
    assert latest["project_id"] == project["id"]
    assert latest["project_name"] == "Demo Project"
    assert latest["application_id"] == application["id"]
    assert latest["application_environment"] == "local"
    assert latest["prompt_version_id"] is not None
    assert latest["model_route_id"] is not None


@requires_database
def test_usage_scopes_returns_seeded_project_and_application() -> None:
    seed_dev_data()

    response = client.get("/v1/usage/scopes")

    assert response.status_code == 200
    scopes = response.json()
    demo_project = next(project for project in scopes if project["slug"] == "demo-project")
    assert demo_project["name"] == "Demo Project"
    assert any(
        application["slug"] == "demo-app" and application["environment"] == "local"
        for application in demo_project["applications"]
    )
