"""Capture synthetic events through actual client builders and sanitizers without network or DB calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)
SENTINEL = "synthetic-private-content-must-not-be-sent"


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_TIME if tz else FIXED_TIME.replace(tzinfo=None)


def capture(client: str, client_root: Path) -> dict:
    sys.dont_write_bytecode = True
    events = {}

    def sender(_endpoint, payload, _key, _timeout):
        assert SENTINEL not in json.dumps(payload)
        events[label] = payload
        return 202

    if client == "proofbase":
        sys.path.insert(0, str(client_root))
        from apps.api.app.observability import auxiliary_telemetry as auxiliary
        from apps.api.app.observability import query_telemetry as query

        sources = [
            auxiliary.__file__,
            query.__file__,
            str(client_root / "apps/api/app/observability/platform_telemetry.py"),
        ]
        settings = SimpleNamespace(
            proofbase_telemetry_enabled=True,
            proofbase_telemetry_endpoint="http://unused.invalid/v1/usage/llm-events",
            proofbase_telemetry_api_key="proofbase-local-placeholder-key-not-a-secret",
            proofbase_telemetry_timeout_seconds=2,
            proofbase_telemetry_max_metadata_bytes=2048,
            proofbase_telemetry_redact_content=True,
        )
        with (
            patch.object(query, "datetime", FixedDateTime),
            patch.object(auxiliary, "datetime", FixedDateTime),
            patch.object(auxiliary, "uuid4", return_value=UUID(int=53)),
        ):
            for operation in ("rag_query", "rag_query_stream"):
                label = operation
                assert query.submit_query_telemetry(
                    request_id="synthetic-query-53",
                    operation_type=operation,
                    status="succeeded",
                    request=SimpleNamespace(
                        question=SENTINEL,
                        session_id="synthetic-session",
                        retrieval_mode="hybrid",
                        chunking_strategy="section_based",
                        top_k=5,
                    ),
                    answer={
                        "model": "gpt-4.1-mini",
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "estimated_cost_usd": "0.000072",
                        "pricing_status": "estimated",
                        "answer": SENTINEL,
                        "citations": [],
                    },
                    trace=SimpleNamespace(
                        retrieval_latency_ms=5, generation_latency_ms=10, total_latency_ms=16
                    ),
                    settings=settings,
                    sender=sender,
                )
            for operation in ("markdown_cleanup", "query_decomposition", "embedding_generation"):
                label = operation
                assert auxiliary.submit_auxiliary_telemetry(
                    operation_type=operation,
                    model="synthetic-model",
                    input_tokens=70,
                    pricing_status="unpriced",
                    question=SENTINEL,
                    document_external_id="synthetic-document",
                    metadata={"embedding_count": 2, "cache_hit": False, "input_json": SENTINEL},
                    settings=settings,
                    sender=sender,
                )
    else:
        sys.path.insert(0, str(client_root / "apps/api"))
        from src.models.agent_step import AgentStep, AgentStepStatus
        from src.models.workflow_run import WorkflowRun, WorkflowStatus
        from src.observability import platform_telemetry as telemetry

        sources = [
            telemetry.__file__,
            str(client_root / "apps/api/src/models/agent_step.py"),
            str(client_root / "apps/api/src/models/workflow_run.py"),
        ]
        settings = SimpleNamespace(
            agentops_telemetry_enabled=True,
            agentops_telemetry_endpoint="http://unused.invalid/v1/usage/llm-events",
            agentops_telemetry_api_key_value="agentops-local-placeholder-key-not-a-secret",
            agentops_telemetry_timeout_seconds=2,
            agentops_telemetry_max_metadata_bytes=2048,
            agentops_telemetry_redact_content=True,
        )
        run = WorkflowRun(
            id=UUID(int=530),
            status=WorkflowStatus.completed,
            total_cost=0.5,
            total_tokens=2000,
            latency_ms=9000,
            retry_count=1,
            completed_at=FIXED_TIME,
        )
        with patch.object(telemetry, "datetime", FixedDateTime):
            for index, response in enumerate(("text", "structured_json"), 1):
                label = response
                step = AgentStep(
                    id=UUID(int=530 + index),
                    workflow_run_id=run.id,
                    agent_name="Synthetic analyst",
                    agent_type="analyst",
                    step_order=index,
                    status=AgentStepStatus.completed,
                    output_json={
                        "final_output" if response == "text" else "key_findings": SENTINEL
                    },
                    model="gpt-4.1-mini",
                    tokens_input=100,
                    tokens_output=50,
                    total_tokens=150,
                    latency_ms=250,
                    cost=0.00012,
                    retry_count=0,
                    completed_at=FIXED_TIME,
                )
                assert telemetry.submit_platform_telemetry(
                    telemetry.build_agent_step_event(step, run=run),
                    active_settings=settings,
                    sender=sender,
                )
            label = "workflow_summary"
            assert telemetry.submit_platform_telemetry(
                telemetry.build_workflow_summary_event(run), active_settings=settings, sender=sender
            )
    return {
        "client": client,
        "synthetic": True,
        "sources": {
            str(Path(path).relative_to(client_root)).replace("\\", "/"): hashlib.sha256(
                Path(path).read_bytes()
            ).hexdigest()
            for path in sources
        },
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=["proofbase", "agentops"], required=True)
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    client_root = args.client_root.resolve(strict=True)
    os.environ["DATABASE_URL"] = "postgresql+psycopg://placeholder:placeholder@127.0.0.1:1/unused"
    os.environ["OPENAI_API_KEY"] = ""
    original = Path.cwd()
    # Imported settings cannot consult a client checkout's .env; submits use synthetic settings.
    with tempfile.TemporaryDirectory(prefix="telemetry-capture-") as temporary:
        try:
            os.chdir(temporary)
            with patch(
                "socket.create_connection",
                side_effect=AssertionError("Network forbidden during capture"),
            ):
                value = capture(args.client, client_root)
        finally:
            os.chdir(original)
    target = ROOT / "contracts/client-captures" / f"{args.client}.json"
    encoded = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    if args.check:
        if target.read_text(encoding="utf-8") != encoded:
            raise SystemExit("Client source or generated telemetry contract changed")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
    print(f"{args.client}: {len(value['events'])} synthetic client events verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
