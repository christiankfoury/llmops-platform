from datetime import UTC, datetime

import pytest
from app.schemas.usage import ExternalLlmEventRequest
from pydantic import ValidationError


def _proofbase_event(operation_type: str, **overrides) -> dict:
    payload = {
        "event_id": f"evt_proofbase_{operation_type}_fixture",
        "external_request_id": f"proofbase_req_{operation_type}_fixture",
        "source_app": "proofbase",
        "operation_type": operation_type,
        "environment": "local",
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": operation_type,
        "prompt_version": "v1",
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
        "estimated_cost_usd": "0.000072",
        "currency": "USD",
        "pricing_status": "estimated",
        "latency_ms": 42,
        "project_external_id": "project-123",
        "department_external_id": "department-456",
        "metadata": {
            "document_count": 1,
            "chunk_count": 2,
            "question_hash": "abc123",
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "operation_type",
    [
        "rag_query",
        "rag_query_stream",
        "markdown_cleanup",
        "query_decomposition",
        "embedding_generation",
    ],
)
def test_proofbase_operation_fixtures_match_external_contract(operation_type: str) -> None:
    payload = _proofbase_event(operation_type)
    if operation_type == "embedding_generation":
        payload.pop("output_tokens")
        payload.pop("total_tokens")
        payload.pop("estimated_cost_usd")
        payload["model"] = "text-embedding-3-small"
        payload["prompt_name"] = None
        payload["prompt_version"] = None
        payload["pricing_status"] = "unpriced"
        payload["metadata"] = {"embedding_count": 8, "cache_hit": False}
    if operation_type == "rag_query_stream":
        payload["metadata"]["streaming"] = True

    event = ExternalLlmEventRequest.model_validate(payload)

    assert event.source_app == "proofbase"
    assert event.operation_type == operation_type
    assert event.environment == "local"
    assert event.model_name == payload["model"]


def test_proofbase_fixture_rejects_sensitive_metadata() -> None:
    payload = _proofbase_event(
        "rag_query",
        metadata={"retrieval_mode": "hybrid", "full_question": "Do not send raw user text"},
    )

    with pytest.raises(ValidationError):
        ExternalLlmEventRequest.model_validate(payload)


def test_failed_proofbase_fixture_requires_error_category() -> None:
    payload = _proofbase_event("query_decomposition", status="failed")

    with pytest.raises(ValidationError):
        ExternalLlmEventRequest.model_validate(payload)

    payload["error_category"] = "provider_error"
    event = ExternalLlmEventRequest.model_validate(payload)
    assert event.status == "failed"
    assert event.error_category == "provider_error"
