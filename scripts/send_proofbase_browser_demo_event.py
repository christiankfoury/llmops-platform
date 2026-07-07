from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEFAULT_API_KEY = "proofbase-local-placeholder-key-not-a-secret"


def build_event(event_id: str, external_request_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "external_request_id": external_request_id,
        "source_app": "proofbase",
        "operation_type": "rag_query",
        "environment": "local",
        "occurred_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "prompt_name": "answer_generation",
        "prompt_version": "v5",
        "input_tokens": 42,
        "output_tokens": 18,
        "total_tokens": 60,
        "estimated_cost_usd": str(Decimal("0.000046")),
        "currency": "USD",
        "pricing_status": "estimated",
        "latency_ms": 321,
        "project_external_id": "proofbase_browser_demo",
        "department_external_id": "demo_department",
        "metadata": {
            "retrieval_mode": "hybrid",
            "chunking_strategy": "section_based",
            "citation_count": 1,
            "response_type": "answer",
            "streaming": False,
            "question_hash": "phase39demoquestionhash",
        },
    }


def post_event(api_base_url: str, api_key: str, payload: dict[str, object]) -> dict:
    endpoint = api_base_url.rstrip("/") + "/v1/usage/llm-events"
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
    )
    with urlopen(request, timeout=15) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one safe Proofbase-shaped telemetry event to a local platform API."
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("PLATFORM_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="Production AI Platform API base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("PROOFBASE_TELEMETRY_API_KEY", DEFAULT_API_KEY),
        help="Local placeholder telemetry API key.",
    )
    parser.add_argument(
        "--event-id",
        default=None,
        help="External event id. Defaults to a unique phase39 demo id.",
    )
    parser.add_argument(
        "--external-request-id",
        default=None,
        help="Proofbase request id shown as the external request id.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    event_id = args.event_id or f"evt_phase39_browser_demo_{suffix}"
    external_request_id = args.external_request_id or f"proofbase_req_phase39_browser_demo_{suffix}"
    payload = build_event(event_id, external_request_id)
    try:
        response = post_event(args.api_base_url, args.api_key, payload)
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"telemetry request failed: HTTP {exc.code} {error_body}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"telemetry request failed: {exc.reason}", file=sys.stderr)
        return 1

    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
