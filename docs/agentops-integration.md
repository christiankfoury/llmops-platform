# AgentOps Integration

AgentOps Workflow Platform is now a connected client app for LLMOps Platform telemetry.

LLMOps Platform centralizes AgentOps operational visibility for agent-step usage, token counts, estimated cost, latency, status, failures, source-app filtering, workflow summaries, and dashboard review. AgentOps still owns the agent workflow layer: workflow execution, agent prompts, structured outputs, tool behavior, workflow input/output state, local evaluation, and per-workflow product UX.

## What Is Connected

The integration is telemetry-first:

- AgentOps can send best-effort LLM usage events to `POST /v1/usage/llm-events`.
- LLMOps Platform authenticates the AgentOps application API key, validates the event contract, persists usage/cost data when present, emits ingestion metrics, and shows the event in the dashboard.
- Dashboard filters can isolate `source_app=agentops` and show `AgentOps Workflow Platform / AgentOps Workflow Platform` traffic.

Covered AgentOps operation types:

- `agent_step`: one model-backed agent step with model, token, latency, status, retry, and estimated-cost data when available.
- `workflow_summary`: one aggregate terminal workflow event for status/latency/retry correlation. These events intentionally omit token and cost fields to avoid central cost double-counting.
- `structured_generation`: allowed by the platform contract for future compatibility, while the current AgentOps implementation represents structured JSON calls as `agent_step` telemetry with `response_type=structured_json`.

## Boundary

LLMOps Platform does not execute AgentOps workflows, route AgentOps tool calls, own AgentOps prompts, inspect generated outputs, parse workflow input/output JSON, evaluate workflow quality, or handle tool payloads.

AgentOps does not need to route provider calls through this gateway for the current integration. The current path centralizes operational telemetry while AgentOps keeps its workflow runtime, local cost tracking, retries, tools, and product behavior.

## Safety Model

Telemetry payloads may include operational fields:

- source app and operation type
- external event/request ids
- provider and model
- prompt name and version identifier when safe
- token counts for model-backed agent steps
- estimated cost for model-backed agent steps
- latency
- status and safe error category
- bounded metadata such as workflow id, agent-step id, agent name/type, step order, retry count, workflow status, step status, and response type

Telemetry payloads must not include:

- platform API keys or provider credentials
- prompt text or system instructions
- generated outputs or structured response JSON
- workflow input/output JSON
- tool arguments or tool results
- raw provider request/response payloads
- user, customer, employee, or incident data

## Failure Behavior

AgentOps telemetry is best-effort. If LLMOps Platform is unavailable, slow, or rejects an event, AgentOps should continue running workflows and record a redacted local diagnostic entry without exposing secrets or workflow payloads.

Expected operator response:

1. Check the platform API health and `/v1/usage/llm-events` logs.
2. Check auth failures, validation errors, duplicate/conflict responses, and database connectivity.
3. Confirm AgentOps is using the expected telemetry endpoint and placeholder/local or environment-specific key.
4. Confirm `AGENTOPS_TELEMETRY_REDACT_CONTENT=true` and metadata size limits remain enabled.
5. Do not disable AgentOps workflows because central telemetry is unavailable.

## Dashboard Interpretation

In authenticated mode, use the dashboard filters to inspect ingested AgentOps traffic.
The default Demo mode shows fixed sample rows and does not query the platform API.
Configure [operator sign-in and project grants](java-operator-security.md) before
using dashboard rows to validate newly submitted events.

- `source_app=agentops` isolates AgentOps traffic from gateway-originated and Proofbase traffic.
- `operation_type=agent_step` shows model-backed agent-step events that may include token and estimated-cost data.
- `operation_type=workflow_summary` shows aggregate terminal workflow status events that should not be treated as billable model calls.
- `response_type=structured_json` indicates a structured generation step without sending the structured output.
- `pricing_status=unknown` or a missing cost means the event is useful for operational correlation but not financial reporting.

Central cost totals should be interpreted as model-step estimated cost. Workflow summaries are intentionally non-billable in the platform so AgentOps step costs are not counted twice.

## Local Validation

Use the browser demo guide:

- [agentops-browser-telemetry-demo.md](agentops-browser-telemetry-demo.md)

Use the contract and cross-repository checks:

```powershell
.\.venv\Scripts\python scripts\validate_agentops_telemetry_contract.py
.\.venv\Scripts\python -m pytest apps/api/tests/test_agentops_telemetry_contract.py apps/api/tests/test_external_telemetry.py -vv
.\.venv\Scripts\python scripts\send_agentops_browser_demo_event.py
```

The sender validates ingestion independently of the dashboard. To inspect its events
in the UI, configure operator sign-in, grant access to the AgentOps project, then open
`http://localhost:3000` and filter **Source App** to `agentops`. Demo mode remains fixed
even after a successful submission; its sample rows are not ingestion evidence.

AgentOps-side checks are optional cross-repository validation. From a checkout of
`agentops-workflow-platform`, with its API virtualenv and test prerequisites installed:

```powershell
.\apps\api\.venv\Scripts\python.exe scripts\test_phase45_mocked_platform_receiver.py
.\apps\api\.venv\Scripts\python.exe scripts\send_platform_telemetry_smoke.py
```

On Unix, use `apps/api/.venv/bin/python`. The platform's default local demo does
not require either client repository.
