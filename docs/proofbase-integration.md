# Proofbase Integration

Proofbase is now a connected client app for Production AI Platform telemetry.

Production AI Platform centralizes Proofbase AI operation visibility for usage, token counts, estimated cost, latency, status, failures, source-app filtering, and dashboard review. Proofbase still owns the AI product layer: document ingestion, scoped retrieval, citation grounding, permission filtering, memory behavior, and benchmark-driven answer quality.

## What Is Connected

The integration is telemetry-first:

- Proofbase sends best-effort LLM usage events to `POST /v1/usage/llm-events`.
- Production AI Platform authenticates the Proofbase application API key, validates the event contract, persists usage/cost data, emits ingestion metrics, and shows the event in the dashboard.
- Dashboard filters can isolate `source_app=proofbase` and show `Proofbase / Enterprise Knowledge Agent` traffic.

Covered Proofbase operation types:

- `rag_query`
- `rag_query_stream`
- `markdown_cleanup`
- `query_decomposition`
- `embedding_generation`

## Boundary

Production AI Platform does not perform Proofbase retrieval, citation validation, permission filtering, document ingestion, memory evaluation, or answer-quality benchmarking.

Proofbase does not need to route provider calls through this gateway for the current integration. Gateway-routed Proofbase calls can be considered later only after the gateway supports Proofbase's richer provider contract and product-safety requirements.

## Safety Model

Telemetry payloads may include operational fields:

- source app and operation type
- external event/request ids
- provider and model
- prompt name and version
- token counts
- estimated cost when available
- latency
- status and error category
- bounded metadata such as retrieval mode, chunking strategy, citation count, response type, and question hash

Telemetry payloads must not include:

- platform API keys or provider credentials
- full prompts or full questions
- rewritten questions
- retrieved chunks
- citation text
- document text
- extracted or cleaned Markdown bodies
- raw provider payloads
- customer, employee, or incident data

## Failure Behavior

Proofbase telemetry is best-effort. If Production AI Platform is unavailable, slow, or rejects an event, Proofbase should continue serving users and record a local diagnostic entry without exposing secrets.

Expected operator response:

1. Check the platform API health and `/v1/usage/llm-events` logs.
2. Check auth failures, validation errors, duplicate/conflict responses, and database connectivity.
3. Confirm Proofbase is using the expected telemetry endpoint and placeholder/local or environment-specific key.
4. Do not disable Proofbase user workflows because central telemetry is unavailable.

## Local Validation

Use the browser demo guide:

- [proofbase-browser-telemetry-demo.md](proofbase-browser-telemetry-demo.md)

Use the contract checks:

```powershell
.\.venv\Scripts\python scripts\validate_proofbase_telemetry_contract.py
.\.venv\Scripts\python -m pytest apps/api/tests/test_proofbase_telemetry_contract.py -vv
.\.venv\Scripts\python scripts\send_proofbase_browser_demo_event.py
```

Then open `http://localhost:3000`, filter **Source App** to `proofbase`, and inspect the resulting dashboard rows.

## AgentOps Handoff

AgentOps Workflow Platform has compatible usage concepts but a different shape from Proofbase.

Observed AgentOps files:

- `apps/api/src/services/llm_client.py`: OpenAI chat calls return model and token usage for text and structured responses.
- `apps/api/src/services/cost_tracking.py`: cost estimation is already centralized around model pricing and agent steps.
- `apps/api/src/models/agent_step.py`: agent steps store model, prompt version, tokens, cost, latency, status, retry count, and error message.
- `apps/api/src/models/cost_event.py`: cost events store per-step token and cost totals.

Reusable platform patterns:

- external app API key registration
- idempotent event ids
- bounded metadata validation
- source-app and operation filters
- local mocked receiver tests
- browser dashboard validation
- redaction rules and non-blocking client behavior

Expected AgentOps differences:

- events should likely map to workflow run and agent step boundaries rather than RAG query boundaries
- operation taxonomy should add agent-oriented names such as `agent_step`, `workflow_step`, or `tool_routing`
- metadata should include safe workflow and agent identifiers, step order, retry count, and tool category without prompts or tool payloads
- cost totals can be reconciled from existing AgentOps `CostEvent` rows

The existing ingestion foundation should support AgentOps without redesign. The next phase sequence should focus on operation taxonomy, safe metadata keys, AgentOps app registration, and client-side best-effort emission.
