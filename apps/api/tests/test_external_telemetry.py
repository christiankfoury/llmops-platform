from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.db.session import SessionLocal
from app.main import app
from fastapi.testclient import TestClient
from scripts.seed_dev_data import AGENTOPS_PLACEHOLDER_API_KEY, PLACEHOLDER_API_KEY
from scripts.seed_dev_data import main as seed_dev_data
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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


def _event_payload(event_id: str | None = None, cost: str = "0.000812") -> dict:
    return {
        "event_id": event_id or f"evt_test_{uuid4().hex}",
        "external_request_id": f"proofbase_req_{uuid4().hex}",
        "source_app": "proofbase",
        "operation_type": "rag_query",
        "environment": "local",
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": "answer_generation",
        "prompt_version": "v5",
        "input_tokens": 1200,
        "output_tokens": 340,
        "total_tokens": 1540,
        "estimated_cost_usd": cost,
        "currency": "USD",
        "pricing_status": "estimated",
        "latency_ms": 1830,
        "project_external_id": "proofbase_project_123",
        "department_external_id": "dept_456",
        "metadata": {
            "retrieval_mode": "hybrid",
            "chunking_strategy": "default",
            "citation_count": 4,
            "response_type": "answer",
            "streaming": False,
        },
    }


def _agentops_workflow_summary_payload(event_id: str | None = None) -> dict:
    return {
        "event_id": event_id or f"evt_agentops_summary_{uuid4().hex}",
        "external_request_id": f"agentops_workflow_{uuid4().hex}",
        "source_app": "agentops",
        "operation_type": "workflow_summary",
        "environment": "local",
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "unknown",
        "model": "unknown",
        "pricing_status": "unknown",
        "latency_ms": 5000,
        "metadata": {
            "workflow_external_id": "workflow_test",
            "workflow_status": "completed",
            "retry_count": 1,
            "response_type": "aggregate_summary",
        },
    }


@requires_database
def test_external_llm_event_is_accepted_and_visible_in_usage() -> None:
    seed_dev_data()
    payload = _event_payload()

    response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json=payload,
    )

    assert response.status_code == 202
    accepted = response.json()
    assert accepted["accepted"] is True
    assert accepted["duplicate"] is False
    assert accepted["external_event_id"] == payload["event_id"]
    assert accepted["external_request_id"] == payload["external_request_id"]

    requests_response = client.get(
        "/v1/usage/requests",
        params={"provider": "openai", "model_name": "gpt-4.1-mini", "limit": 100},
    )
    assert requests_response.status_code == 200
    records = requests_response.json()
    external_record = next(
        record for record in records if record["external_event_id"] == payload["event_id"]
    )
    assert external_record["source_app"] == "proofbase"
    assert external_record["operation_type"] == "rag_query"
    assert external_record["external_request_id"] == payload["external_request_id"]
    assert external_record["estimated_input_tokens"] == 1200
    assert external_record["estimated_output_tokens"] == 340

    summary_response = client.get(
        "/v1/usage/summary",
        params={"provider": "openai", "model_name": "gpt-4.1-mini", "status": "succeeded"},
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["request_count"] >= 1
    assert Decimal(summary["estimated_cost_usd"]) >= Decimal(payload["estimated_cost_usd"])

    metrics_response = client.get("/metrics")
    assert "llm_external_telemetry_events_total" in metrics_response.text
    assert "llm_external_telemetry_estimated_cost_usd_total" in metrics_response.text
    assert "llm_external_telemetry_tokens_total" in metrics_response.text


@requires_database
def test_external_llm_event_rejects_invalid_api_key_without_persistence() -> None:
    seed_dev_data()
    payload = _event_payload()

    response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": "not-a-real-key"},
        json=payload,
    )

    assert response.status_code == 401

    with SessionLocal() as db:
        persisted_count = db.scalar(
            text("select count(*) from gateway_requests where external_event_id = :event_id"),
            {"event_id": payload["event_id"]},
        )
    assert persisted_count == 0


@requires_database
def test_external_llm_event_rejects_sensitive_metadata_without_persistence() -> None:
    seed_dev_data()
    payload = _event_payload()
    payload["metadata"] = {"prompt": "do not store me"}

    response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json=payload,
    )

    assert response.status_code == 422

    with SessionLocal() as db:
        persisted_count = db.scalar(
            text("select count(*) from gateway_requests where external_event_id = :event_id"),
            {"event_id": payload["event_id"]},
        )
    assert persisted_count == 0


@requires_database
def test_external_llm_event_duplicate_does_not_double_count_cost() -> None:
    seed_dev_data()
    event_id = f"evt_duplicate_{uuid4().hex}"
    payload = _event_payload(event_id=event_id)

    first_response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json=payload,
    )
    second_response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json=payload,
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.json()["duplicate"] is True

    with SessionLocal() as db:
        rows = db.execute(
            text(
                "select gr.id, count(cr.id) as cost_records "
                "from gateway_requests gr "
                "left join cost_records cr on cr.gateway_request_id = gr.id "
                "where gr.external_event_id = :event_id "
                "group by gr.id"
            ),
            {"event_id": event_id},
        ).all()

    assert len(rows) == 1
    assert rows[0].cost_records == 1


@requires_database
def test_external_llm_event_duplicate_conflict_is_rejected() -> None:
    seed_dev_data()
    event_id = f"evt_conflict_{uuid4().hex}"
    payload = _event_payload(event_id=event_id)
    changed_payload = dict(payload)
    changed_payload["estimated_cost_usd"] = "0.002000"

    first_response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json=payload,
    )
    conflict_response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": PLACEHOLDER_API_KEY},
        json=changed_payload,
    )

    assert first_response.status_code == 202
    assert conflict_response.status_code == 409


@requires_database
def test_agentops_workflow_summary_event_is_accepted_without_cost_record() -> None:
    seed_dev_data()
    payload = _agentops_workflow_summary_payload()

    response = client.post(
        "/v1/usage/llm-events",
        headers={"X-API-Key": AGENTOPS_PLACEHOLDER_API_KEY},
        json=payload,
    )

    assert response.status_code == 202
    accepted = response.json()
    assert accepted["accepted"] is True
    assert accepted["duplicate"] is False

    with SessionLocal() as db:
        row = db.execute(
            text(
                "select gr.source_app, gr.operation_type, gr.estimated_cost_usd, "
                "count(cr.id) as cost_records "
                "from gateway_requests gr "
                "left join cost_records cr on cr.gateway_request_id = gr.id "
                "where gr.external_event_id = :event_id "
                "group by gr.id"
            ),
            {"event_id": payload["event_id"]},
        ).one()

    assert row.source_app == "agentops"
    assert row.operation_type == "workflow_summary"
    assert row.estimated_cost_usd is None
    assert row.cost_records == 0
