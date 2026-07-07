from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.schemas.usage import ExternalLlmEventRequest  # noqa: E402


def _event(operation_type: str) -> dict:
    payload = {
        "event_id": f"evt_proofbase_{operation_type}_smoke",
        "external_request_id": f"proofbase_req_{operation_type}_smoke",
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
        "metadata": {"question_hash": "abc123"},
    }
    if operation_type == "embedding_generation":
        payload.pop("output_tokens")
        payload.pop("total_tokens")
        payload.pop("estimated_cost_usd")
        payload["model"] = "text-embedding-3-small"
        payload["prompt_name"] = None
        payload["prompt_version"] = None
        payload["pricing_status"] = "unpriced"
        payload["metadata"] = {"embedding_count": 3, "cache_hit": False}
    return payload


def main() -> None:
    operations = [
        "rag_query",
        "rag_query_stream",
        "markdown_cleanup",
        "query_decomposition",
        "embedding_generation",
    ]
    for operation in operations:
        ExternalLlmEventRequest.model_validate(_event(operation))
    print(f"validated {len(operations)} Proofbase telemetry event fixtures")


if __name__ == "__main__":
    main()
