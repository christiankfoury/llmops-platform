"""Language-neutral fixtures and boundary regressions for the Java conversion."""

import copy
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from app.api import gateway
from app.db.session import SessionLocal, get_db
from app.main import app
from app.schemas.gateway import CompletionResponse
from app.schemas.usage import ExternalLlmEventRequest, UsageSummary
from app.services.gateway import GatewayAuthError, GatewayConfigError, GatewayProviderError
from app.services.pricing import calculate_estimated_cost
from app.services.usage import _payload_fingerprint, _six_decimal_cost
from fastapi.testclient import TestClient
from pydantic import ValidationError
from scripts.seed_dev_data import AGENTOPS_PLACEHOLDER_API_KEY, PROOFBASE_PLACEHOLDER_API_KEY
from scripts.seed_dev_data import main as seed_dev_data
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

BASELINE = Path(__file__).resolve().parents[3] / "contracts/python-baseline"
FIXTURES = json.loads((BASELINE / "telemetry-fixtures.json").read_text(encoding="utf-8"))
GOLDEN = json.loads((BASELINE / "telemetry-golden.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", FIXTURES)
def test_telemetry_normalization_and_fingerprint(name: str) -> None:
    payload = ExternalLlmEventRequest.model_validate(FIXTURES[name])
    assert payload.model_dump(mode="json", by_alias=True) == GOLDEN[name]["normalized"]
    assert _payload_fingerprint(payload) == GOLDEN[name]["fingerprint"]
    reversed_keys = dict(reversed(list(FIXTURES[name].items())))
    assert (
        _payload_fingerprint(ExternalLlmEventRequest.model_validate(reversed_keys))
        == (GOLDEN[name]["fingerprint"])
    )


@pytest.mark.parametrize(
    "change",
    [
        {"prompt": "synthetic forbidden field"},
        {"metadata": {"prompt": "synthetic forbidden field"}},
        {"metadata": {"tool_arguments": "synthetic forbidden field"}},
        {"metadata": {"response_type": {"nested": True}}},
        {"occurred_at": "2026-01-02T03:04:05"},
        {"input_tokens": -1},
        {"total_tokens": 999},
        {"estimated_cost_usd": "-0.1"},
        {"currency": "EUR"},
        {"status": "failed"},
    ],
)
def test_rejected_telemetry_boundaries(change: dict) -> None:
    with pytest.raises(ValidationError):
        ExternalLlmEventRequest.model_validate({**FIXTURES["proofbase_query"], **change})


def test_decimal_wire_format_and_distinct_rounding_rules() -> None:
    summary = UsageSummary(
        request_count=0,
        error_count=0,
        average_latency_ms=0,
        estimated_cost_usd=Decimal("0.000000"),
    )
    assert summary.model_dump(mode="json")["estimated_cost_usd"] == "0.000000"
    # Gateway rounds half-up; telemetry currently uses decimal's default half-even.
    assert calculate_estimated_cost("mock", "mock-llm-small", 5, 0) == Decimal("0.000001")
    assert _six_decimal_cost(Decimal("0.0000005")) == Decimal("0.000000")
    assert _six_decimal_cost(Decimal("0.0000015")) == Decimal("0.000002")
    assert _six_decimal_cost(None) is None


def test_legacy_fingerprint_distinguishes_decimal_scale_and_timezone_representation() -> None:
    raw = FIXTURES["proofbase_normalization_edges"]
    original = ExternalLlmEventRequest.model_validate(raw)
    changed_scale = ExternalLlmEventRequest.model_validate(
        {**raw, "estimated_cost_usd": "0.0000001"}
    )
    changed_offset = ExternalLlmEventRequest.model_validate(
        {
            **raw,
            "occurred_at": "2026-01-02T03:04:13.123456Z",
        }
    )
    assert original.estimated_cost_usd == changed_scale.estimated_cost_usd
    assert original.occurred_at == changed_offset.occurred_at
    assert _payload_fingerprint(original) != _payload_fingerprint(changed_scale)
    assert _payload_fingerprint(original) != _payload_fingerprint(changed_offset)


@pytest.fixture
def boundary_client(monkeypatch):
    # These tests cover the HTTP boundary. PostgreSQL semantics are checked separately below.
    app.dependency_overrides[get_db] = lambda: None
    monkeypatch.setattr(gateway, "check_rate_limit", lambda **kwargs: True)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (GatewayAuthError("Invalid API key"), 401, "Invalid API key"),
        (GatewayConfigError("No active prompt found"), 404, "No active prompt found"),
        (
            GatewayProviderError(
                "Mock provider failed", error_category="provider_error", status_code=502
            ),
            502,
            "Mock provider failed",
        ),
        (
            GatewayProviderError(
                "Mock provider timed out", error_category="provider_timeout", status_code=504
            ),
            504,
            "Mock provider timed out",
        ),
    ],
)
def test_gateway_error_envelope(boundary_client, monkeypatch, error, status_code, detail):
    def fail(**kwargs):
        raise error

    monkeypatch.setattr(gateway, "process_completion", fail)
    response = boundary_client.post(
        "/v1/gateway/completions",
        json={"input": "synthetic request"},
        headers={"X-API-Key": "contract-placeholder", "X-Request-ID": "contract-http-1"},
    )
    assert response.status_code == status_code
    assert response.json() == {"detail": detail}
    assert response.headers["X-Request-ID"] == "contract-http-1"


def test_gateway_success_and_rejection_boundaries(boundary_client, monkeypatch):
    monkeypatch.setattr(
        gateway,
        "process_completion",
        lambda **kwargs: CompletionResponse(
            request_id="req_contract",
            status="succeeded",
            provider="mock",
            model="mock-llm-small",
            output="synthetic response",
            prompt_version=1,
            latency_ms=1,
            input_tokens=5,
            output_tokens=1,
            estimated_cost_usd=Decimal("0.000001"),
        ),
    )
    request = {"input": "synthetic request"}
    response = boundary_client.post("/v1/gateway/completions", json=request)
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing API key"}
    headers = {"X-API-Key": "contract-placeholder"}
    response = boundary_client.post("/v1/gateway/completions", json=request, headers=headers)
    assert response.status_code == 200
    assert response.json()["estimated_cost_usd"] == "0.000001"
    response = boundary_client.post("/v1/gateway/completions", json={"input": ""}, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "input"]
    monkeypatch.setattr(gateway, "check_rate_limit", lambda **kwargs: False)
    response = boundary_client.post("/v1/gateway/completions", json=request, headers=headers)
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}


def test_postgresql_fixture_lifecycle_and_usage_filters() -> None:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
    except SQLAlchemyError:
        if os.environ.get("REQUIRE_DATABASE_TESTS") == "true":
            pytest.fail("PostgreSQL contract validation is required but unavailable")
        pytest.skip("PostgreSQL unavailable; CI requires this contract test")
    seed_dev_data()
    with TestClient(app) as client:
        for name, raw in FIXTURES.items():
            headers = {
                "X-API-Key": (
                    AGENTOPS_PLACEHOLDER_API_KEY
                    if name.startswith("agentops")
                    else PROOFBASE_PLACEHOLDER_API_KEY
                )
            }
            first = client.post("/v1/usage/llm-events", json=raw, headers=headers)
            assert first.status_code == 202
            second = client.post("/v1/usage/llm-events", json=raw, headers=headers)
            assert second.status_code == 202
            assert second.json()["duplicate"] is True
            assert second.json()["request_id"] == first.json()["request_id"]
            changed = copy.deepcopy(raw)
            changed["latency_ms"] = 9876
            assert (
                client.post("/v1/usage/llm-events", json=changed, headers=headers).status_code
                == 409
            )
            with SessionLocal() as db:
                costs = db.scalar(
                    text(
                        "select count(cr.id) from cost_records cr join gateway_requests gr "
                        "on cr.gateway_request_id = gr.id where gr.request_id = :request_id"
                    ),
                    {"request_id": first.json()["request_id"]},
                )
            assert costs == (1 if "estimated_cost_usd" in raw else 0)
        query = client.get(
            "/v1/usage/requests",
            params={
                "source_app": "proofbase",
                "operation_type": "rag_query",
                "provider": "openai",
                "model_name": "gpt-4.1-mini",
                "status": "succeeded",
                "created_from": "2026-01-02T03:04:05.123456Z",
                "created_to": "2026-01-02T03:04:05.123456Z",
                "limit": 500,
            },
        )
        assert query.status_code == 200
        assert len(query.json()) == 1
        record = query.json()[0]
        assert record["external_event_id"] == "contract_proofbase_query"
        assert record["estimated_cost_usd"] == "0.000072"
        assert datetime.fromisoformat(record["created_at"]) == datetime.fromisoformat(
            "2026-01-02T03:04:05.123456+00:00"
        )
        # Exercise operator create/update/activate/list on isolated synthetic configuration.
        # Authentication is intentionally added later; this records the private reference API.
        for resource, create_body, patch_body in [
            (
                "prompt-versions",
                {
                    "project_slug": "demo-project",
                    "application_slug": "demo-app",
                    "name": "contract-chat",
                    "content": "Synthetic contract prompt",
                    "is_active": False,
                },
                {"content": "Updated synthetic contract prompt"},
            ),
            (
                "model-routes",
                {
                    "project_slug": "demo-project",
                    "application_slug": "demo-app",
                    "environment": "contract",
                    "provider": "mock",
                    "model_name": "mock-llm-small",
                    "is_active": False,
                    "is_default": False,
                },
                {"priority": 25},
            ),
        ]:
            path = f"/v1/admin/{resource}"
            created = client.post(path, json=create_body, headers={"X-Actor-ID": "contract-actor"})
            assert created.status_code == 201
            record_id = created.json()["id"]
            updated = client.patch(f"{path}/{record_id}", json=patch_body)
            assert updated.status_code == 200
            assert all(updated.json()[key] == value for key, value in patch_body.items())
            activated = client.post(f"{path}/{record_id}/activate")
            assert activated.status_code == 200
            assert activated.json()["is_active"] is True
            listed = client.get(path)
            assert listed.status_code == 200
            assert any(row["id"] == record_id for row in listed.json())
