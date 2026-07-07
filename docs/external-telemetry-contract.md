# External Telemetry Contract

This contract defines the telemetry-first integration path for external AI applications that already call model providers directly.

Phase 31 focuses on Proofbase (`enterprise-knowledge-agent`) first. AgentOps Workflow Platform should reuse the same ingestion model later, after the Proofbase path is working end to end.

## Integration Goal

Production AI Platform should centralize LLMOps visibility for external applications without taking over their product-layer behavior.

For Proofbase, that means:

- Proofbase keeps owning RAG, retrieval, citations, permissions, memory behavior, document workflows, and answer-quality evaluation.
- Production AI Platform receives normalized events for model usage, estimated cost, latency, status, token usage, request IDs, and bounded metadata.
- Proofbase continues to work if Production AI Platform is unavailable.

This phase does not route Proofbase provider calls through the gateway. Gateway-routed Proofbase calls are a later option after the gateway supports the richer RAG provider contract.

## Endpoint Shape

Phase 32 should implement an ingestion endpoint with this logical shape:

```text
POST /v1/usage/llm-events
X-API-Key: <application API key>
Idempotency-Key: <optional stable event key>
```

The API key identifies the calling Production AI Platform application record. The request body identifies the external operation and usage facts.

## Event Schema

Example payload:

```json
{
  "event_id": "evt_proofbase_01HZT1EXAMPLE000001",
  "external_request_id": "proofbase_req_01HZT1EXAMPLE000001",
  "source_app": "proofbase",
  "operation_type": "rag_query",
  "environment": "local",
  "occurred_at": "2026-07-06T14:30:00Z",
  "status": "succeeded",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "prompt_name": "answer_generation",
  "prompt_version": "v5",
  "input_tokens": 1200,
  "output_tokens": 340,
  "total_tokens": 1540,
  "estimated_cost_usd": "0.000812",
  "currency": "USD",
  "pricing_status": "estimated",
  "latency_ms": 1830,
  "error_category": null,
  "project_external_id": "proofbase_project_123",
  "department_external_id": "dept_456",
  "metadata": {
    "retrieval_mode": "hybrid",
    "chunking_strategy": "default",
    "citation_count": 4,
    "response_type": "answer",
    "streaming": false
  }
}
```

### Required Fields

| Field | Type | Notes |
|---|---|---|
| `event_id` | string | Stable client-generated event ID. Used for idempotency and duplicate suppression. |
| `external_request_id` | string | Stable request/workflow ID from the client app. Multiple operations can share one external request ID. |
| `source_app` | string | Bounded slug such as `proofbase` or, later, `agentops-workflow-platform`. |
| `operation_type` | string enum | One of the operation types listed below. |
| `environment` | string | Bounded environment value such as `local`, `dev`, `staging`, or `prod`. |
| `occurred_at` | RFC 3339 timestamp | When the model operation completed or failed in the source app. |
| `status` | string enum | `succeeded`, `failed`, or `skipped`. |
| `provider` | string | Provider slug such as `openai`, `anthropic`, `mock`, or `unknown`. |
| `model` | string | Provider model name when known. Use `unknown` only when the caller cannot safely determine it. |

### Optional Fields

| Field | Type | Notes |
|---|---|---|
| `prompt_name` | string | Logical prompt family, not full prompt text. |
| `prompt_version` | string | Source app prompt version, for example Proofbase `answer_generation_v5`. |
| `input_tokens` | integer | Prompt/input tokens when available. Must be non-negative. |
| `output_tokens` | integer | Completion/output tokens when available. Must be non-negative. |
| `total_tokens` | integer | Optional total. The API may compute it when both token fields are present. |
| `estimated_cost_usd` | decimal string | Estimated USD cost. Not billing-grade. |
| `currency` | string | Defaults to `USD` when `estimated_cost_usd` is present. |
| `pricing_status` | string | `estimated`, `unpriced`, `cached`, or `unknown`. |
| `latency_ms` | integer | Total model-operation latency when available. |
| `retrieval_latency_ms` | integer | Proofbase-specific retrieval latency. Use as metadata only in gateway summaries if needed. |
| `generation_latency_ms` | integer | Proofbase-specific generation latency. |
| `error_category` | string | Bounded category such as `provider_error`, `provider_timeout`, `validation_error`, `rate_limited`, or `unknown`. Required when `status` is `failed` if known. |
| `error_message_redacted` | string | Short sanitized message. No prompts, document text, provider payloads, or secrets. |
| `project_external_id` | string | Source app project identifier. It is not a Production AI Platform project UUID. |
| `department_external_id` | string | Optional Proofbase department identifier. |
| `metadata` | object | Bounded sanitized operational metadata. Keys and values must be allowlisted by the source app. |

## Operation Taxonomy

Proofbase should start with these operation types:

| Operation type | Proofbase source | Meaning |
|---|---|---|
| `rag_query` | `/query` and `generation/answer_generator.py` | One non-streaming RAG answer generation request. |
| `rag_query_stream` | `/query/stream` and `generation/answer_generator.py` | One streaming RAG answer generation request. Emit one final event per stream. |
| `markdown_cleanup` | `projects/markdown_cleanup.py` | AI cleanup of extracted Markdown before human review. |
| `query_decomposition` | reasoning/query-decomposition path | AI-assisted decomposition or rewriting used before retrieval or generation. |
| `embedding_generation` | `embeddings/openai_embeddings.py` and document indexing paths | Embedding provider call for query or document chunks. |

AgentOps should add its own operation types later only after Phase 40. Expected examples are `workflow_run`, `agent_step`, `tool_call`, and `workflow_summary`, but those are not part of the Proofbase acceptance criteria.

## Sensitive Data Rules

External telemetry must not include these values by default:

- Production AI Platform API keys.
- Provider API keys or credentials.
- Authorization headers, cookies, session tokens, or database connection strings.
- Full prompts or system messages.
- Full user questions.
- Rewritten questions.
- Retrieved chunks.
- Citation text or citation excerpts.
- Uploaded document text.
- Extracted Markdown or cleaned Markdown.
- Raw customer, employee, tenant, or personal data.
- Provider request or response bodies.

Allowed metadata should be operational and bounded:

- `retrieval_mode`
- `chunking_strategy`
- `top_k`
- `citation_count`
- `response_type`
- `streaming`
- `cache_hit`
- `document_count`
- `chunk_count`
- `embedding_count`

If the source app needs correlation without content, it should send hashes or opaque IDs such as `question_hash`, `document_external_id`, or `session_external_id`. Hashes must be deterministic only inside the source app's trust boundary and must not allow easy reconstruction of sensitive content.

## Idempotency Strategy

The source app should generate a stable `event_id` for each logical model operation.

Recommended uniqueness rule:

```text
(application_id, event_id)
```

The ingestion API should reject or acknowledge duplicates without creating a second request or cost record. A duplicate event with the same payload can return success with `duplicate: true`. A duplicate event ID with conflicting payload fields should return a validation error and should not mutate stored usage totals.

`external_request_id` groups related events from the source app. For example, one Proofbase request can have:

- one `query_decomposition` event
- one `embedding_generation` event
- one `rag_query` or `rag_query_stream` event

`external_request_id` is for correlation. `event_id` is for idempotency.

## Error And Retry Semantics

Telemetry submission is best-effort for source apps.

Client behavior:

- Use a short timeout.
- Do not block a successful user workflow on telemetry delivery.
- Retry transient HTTP `408`, `429`, and `5xx` responses with bounded backoff when it is cheap and safe.
- Do not retry HTTP `400`, `401`, `403`, or schema validation errors until configuration or code is fixed.
- Log telemetry failures locally with redacted context only.
- Avoid writing failed telemetry payloads to durable local files unless those files follow the same sensitive-data rules.

Platform behavior:

- Validate schema before persistence.
- Authenticate the application API key before trusting `source_app`.
- Persist accepted events atomically with usage/cost records.
- Never create partial cost records for rejected events.
- Emit ingestion metrics for accepted, rejected, duplicate, and failed submissions.
- Preserve the original `event_id` and `external_request_id` in request detail views.

## Proofbase Field Mapping

Proofbase already has local request/cost fields that can map to this contract:

| Proofbase field | Contract field |
|---|---|
| `request_id` | `external_request_id` |
| generated telemetry event UUID | `event_id` |
| `prompt_version` | `prompt_version` |
| `model` | `model` |
| `input_tokens` | `input_tokens` |
| `output_tokens` | `output_tokens` |
| `estimated_cost_usd` | `estimated_cost_usd` |
| `pricing_status` | `pricing_status` |
| `retrieval_latency_ms` | `retrieval_latency_ms` |
| `generation_latency_ms` | `generation_latency_ms` |
| `total_latency_ms` | `latency_ms` |
| sanitized local error category | `error_category` |
| `project_id` | `project_external_id` |
| `department_id` | `department_external_id` |

Proofbase's local observability log may keep app-local diagnostics such as truncated questions. Those fields must not cross into Production AI Platform telemetry unless a later privacy review explicitly approves them.

## Phase Notes

Phase 32 should implement the Production AI Platform ingestion API from this contract.

Phases 33-39 should connect Proofbase one operation group at a time:

1. Register Proofbase as a platform application.
2. Add Proofbase telemetry configuration and a best-effort client.
3. Emit RAG query and streaming telemetry.
4. Emit Markdown cleanup, query decomposition, and embedding telemetry.
5. Validate with mocked tests and a browser demo.

Phase 40 should close the Proofbase sequence and define the AgentOps handoff using the same external telemetry model.
