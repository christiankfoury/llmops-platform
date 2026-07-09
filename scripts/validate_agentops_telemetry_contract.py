from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.schemas.usage import ExternalLlmEventRequest  # noqa: E402


def _event(operation_type: str) -> dict:
    payload = {
        "event_id": f"evt_agentops_{operation_type}_smoke",
        "external_request_id": f"agentops_workflow_{operation_type}_smoke",
        "source_app": "agentops",
        "operation_type": operation_type,
        "environment": "local",
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": operation_type,
        "prompt_version": "workflow-prompt-v1",
        "input_tokens": 100,
        "output_tokens": 25,
        "total_tokens": 125,
        "estimated_cost_usd": "0.000080",
        "currency": "USD",
        "pricing_status": "estimated",
        "latency_ms": 95,
        "metadata": {
            "workflow_external_id": "workflow_run_smoke",
            "agent_step_external_id": "agent_step_smoke",
            "agent_name": "analyst",
            "agent_type": "analysis",
            "step_order": 1,
            "retry_count": 0,
            "workflow_status": "running",
            "step_status": "completed",
            "response_type": "text",
        },
    }
    if operation_type == "structured_generation":
        payload["metadata"]["response_type"] = "structured_json"
    if operation_type == "workflow_summary":
        payload.pop("estimated_cost_usd")
        payload["pricing_status"] = "unknown"
        payload["metadata"].pop("agent_step_external_id")
        payload["metadata"].pop("step_order")
        payload["metadata"].pop("step_status")
        payload["metadata"]["workflow_status"] = "completed"
    return payload


def main() -> None:
    operations = [
        "agent_step",
        "structured_generation",
        "workflow_summary",
    ]
    for operation in operations:
        ExternalLlmEventRequest.model_validate(_event(operation))
    print(f"validated {len(operations)} AgentOps telemetry event fixtures")


if __name__ == "__main__":
    main()
