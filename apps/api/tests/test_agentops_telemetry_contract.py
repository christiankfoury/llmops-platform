from datetime import UTC, datetime

import pytest
from app.schemas.usage import ExternalLlmEventRequest
from pydantic import ValidationError


def _agentops_event(operation_type: str, **overrides) -> dict:
    payload = {
        "event_id": f"evt_agentops_{operation_type}_fixture",
        "external_request_id": f"agentops_workflow_{operation_type}_fixture",
        "source_app": "agentops",
        "operation_type": operation_type,
        "environment": "local",
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": operation_type,
        "prompt_version": "workflow-prompt-v1",
        "input_tokens": 800,
        "output_tokens": 220,
        "total_tokens": 1020,
        "estimated_cost_usd": "0.000672",
        "currency": "USD",
        "pricing_status": "estimated",
        "latency_ms": 1210,
        "project_external_id": "agentops_org_123",
        "metadata": {
            "workflow_external_id": "workflow_run_123",
            "agent_step_external_id": "agent_step_456",
            "agent_name": "analyst",
            "agent_type": "analysis",
            "step_order": 2,
            "retry_count": 1,
            "workflow_status": "running",
            "step_status": "completed",
            "response_type": "text",
        },
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "operation_type",
    [
        "agent_step",
        "structured_generation",
        "workflow_summary",
    ],
)
def test_agentops_operation_fixtures_match_external_contract(operation_type: str) -> None:
    payload = _agentops_event(operation_type)
    if operation_type == "structured_generation":
        payload["metadata"]["response_type"] = "structured_json"
    if operation_type == "workflow_summary":
        payload.pop("estimated_cost_usd")
        payload["pricing_status"] = "unknown"
        payload["metadata"].pop("agent_step_external_id")
        payload["metadata"].pop("step_order")
        payload["metadata"].pop("step_status")
        payload["metadata"]["workflow_status"] = "completed"

    event = ExternalLlmEventRequest.model_validate(payload)

    assert event.source_app == "agentops"
    assert event.operation_type == operation_type
    assert event.metadata["workflow_external_id"] == "workflow_run_123"
    assert event.model_name == payload["model"]


@pytest.mark.parametrize(
    "field_name",
    [
        "prompt",
        "generated_output",
        "workflow_json",
        "tool_payload",
        "provider_payload",
        "api_key",
    ],
)
def test_agentops_fixture_rejects_sensitive_top_level_fields(field_name: str) -> None:
    payload = _agentops_event("agent_step")
    payload[field_name] = "must not be accepted"

    with pytest.raises(ValidationError):
        ExternalLlmEventRequest.model_validate(payload)


@pytest.mark.parametrize(
    "metadata",
    [
        {"input_json": {"customer": "raw workflow input"}},
        {"output_json": {"result": "raw generated output"}},
        {"tool_result": "raw tool payload"},
        {"prompt": "raw prompt text"},
    ],
)
def test_agentops_fixture_rejects_sensitive_metadata(metadata: dict) -> None:
    payload = _agentops_event("agent_step", metadata=metadata)

    with pytest.raises(ValidationError):
        ExternalLlmEventRequest.model_validate(payload)


def test_failed_agentops_fixture_requires_error_category() -> None:
    payload = _agentops_event("agent_step", status="failed")

    with pytest.raises(ValidationError):
        ExternalLlmEventRequest.model_validate(payload)

    payload["error_category"] = "provider_error"
    event = ExternalLlmEventRequest.model_validate(payload)
    assert event.status == "failed"
    assert event.error_category == "provider_error"
