> Historical document. Current behavior and scope are described in the [documentation index](../README.md).

# AgentOps Integration Plan

AgentOps Workflow Platform is integrated as the second client app for Production AI Platform telemetry.

The implementation uses Proofbase as the proven reference pattern, but it does not copy Proofbase's RAG-specific event names or metadata. AgentOps is a workflow/agent-step application, so telemetry is derived from AgentOps workflow runs, agent steps, structured generation calls, retries, and cost events.

## Strategy

Use Proofbase as the anti-hallucination anchor:

- reuse the same platform ingestion endpoint pattern
- reuse the same best-effort client behavior
- reuse the same env-switch shape
- reuse the same redaction and bounded metadata discipline
- reuse the same mocked receiver and browser validation style

Adapt to AgentOps:

- derive fields from `WorkflowRun`, `AgentStep`, and `CostEvent`
- avoid Proofbase-only terms such as RAG query, retrieval mode, citation count, department id, document id, chunking strategy, and answer citations
- do not send prompts, generated outputs, tool payloads, workflow inputs, or sensitive intermediate JSON
- preserve AgentOps local cost tracking as the source application view while sending normalized operational telemetry to Production AI Platform

## Switch

AgentOps should be able to run with or without Production AI Platform.

Default local config should be off:

```env
AGENTOPS_TELEMETRY_ENABLED=false
AGENTOPS_TELEMETRY_ENDPOINT=http://localhost:8000/v1/usage/llm-events
AGENTOPS_TELEMETRY_API_KEY=agentops-local-placeholder-key-not-a-secret
AGENTOPS_TELEMETRY_TIMEOUT_SECONDS=2
AGENTOPS_TELEMETRY_MAX_METADATA_BYTES=2048
AGENTOPS_TELEMETRY_REDACT_CONTENT=true
```

When AgentOps runs inside Docker and Production AI Platform runs on the host:

```env
AGENTOPS_TELEMETRY_ENDPOINT=http://host.docker.internal:8000/v1/usage/llm-events
```

## Reference Files

Proofbase reference implementation:

- `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\platform_telemetry.py`
- `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\query_telemetry.py`
- `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\auxiliary_telemetry.py`
- `S:\github-repos\enterprise-knowledge-agent\scripts\test_platform_telemetry_client.py`
- `S:\github-repos\enterprise-knowledge-agent\scripts\test_phase38_mocked_platform_receiver.py`
- `docs/proofbase-integration.md`
- `docs/proofbase-browser-telemetry-demo.md`

AgentOps implementation targets:

- `S:\github-repos\agentops-workflow-platform\apps\api\src\services\llm_client.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\services\cost_tracking.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\models\agent_step.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\models\cost_event.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\models\workflow_run.py`
- AgentOps `.env.example`, README, scripts, and tests

Production AI Platform targets:

- `apps/api/app/schemas/usage.py`
- `apps/api/app/services/usage.py`
- `apps/api/scripts/seed_dev_data.py`
- `apps/api/tests/`
- `apps/web/components/dashboard.tsx`
- `docs/testing.md`
- `docs/dashboard-screenshots.md`
- `docs/portfolio-demo-plan.md`

## Event Mapping

Recommended source app:

```text
agentops
```

Recommended initial operation types:

- `agent_step`: one completed or failed agent step with model/token/cost/latency data
- `structured_generation`: a structured JSON generation call, when distinguishable from plain text generation
- `workflow_summary`: one summary event for a workflow run after completion, if the data is not duplicative

Possible later operation types:

- `tool_planning`
- `tool_execution`
- `workflow_retry`

Safe metadata candidates:

- `workflow_external_id`
- `agent_step_external_id`
- `agent_name`
- `agent_type`
- `step_order`
- `retry_count`
- `workflow_status`
- `step_status`
- `response_type`
- `pricing_status`

Do not send:

- workflow input JSON
- agent output JSON
- prompt text
- system instructions
- generated content
- tool arguments or tool results
- provider request/response payloads
- user data or customer data
- API keys or provider credentials

## Implementation Phases

### Phase 41: AgentOps Contract And Platform Registration

Define the AgentOps operation taxonomy and platform-side compatibility.

Deliverables:

- Extend external telemetry operation types for AgentOps.
- Add safe AgentOps metadata keys.
- Register AgentOps as a local seeded project/application with a placeholder API key.
- Add schema tests for AgentOps-shaped events.
- Update docs and `.env.example` placeholders.

Acceptance:

- AgentOps event fixtures validate locally.
- Proofbase event fixtures still validate.
- No prompt/output/tool payload fields are accepted.

### Phase 42: AgentOps Telemetry Client And Switch

Implement a best-effort telemetry client inside AgentOps.

Deliverables:

- Add AgentOps env settings with `AGENTOPS_TELEMETRY_ENABLED=false` by default.
- Add a telemetry client with timeout, disabled mode, payload-size guard, and redacted error logging.
- Add a smoke script that sends one safe AgentOps-shaped event.
- Add unit tests for disabled mode, successful send, receiver failure, timeout/failure isolation, and redaction.

Acceptance:

- AgentOps works normally when telemetry is disabled.
- AgentOps user workflows do not fail when Production AI Platform is down.
- No secrets or raw workflow content are logged or sent.

### Phase 43: Agent Step Telemetry Emission

Emit central telemetry for AgentOps agent steps.

Deliverables:

- Hook into the AgentOps step completion/failure path.
- Send one `agent_step` event per completed or failed step where model/token/latency data is available.
- Map model, input/output tokens, total tokens, estimated cost, latency, status, retry count, agent name/type, and step order.
- Avoid workflow input/output JSON.
- Add tests for successful step telemetry and failed step telemetry.

Acceptance:

- Completed agent steps appear in Production AI Platform under `source_app=agentops`.
- Failed agent steps include safe failure status/category.
- AgentOps local cost tracking remains unchanged.

### Phase 44: Structured Generation And Workflow Summary Telemetry

Cover additional AgentOps AI paths without double-counting cost.

Implementation decision:

- Structured JSON generation stays represented as `agent_step` telemetry with `response_type=structured_json` because each structured call already corresponds to one model-backed step and one local cost event.
- Writer and baseline text calls are represented as `agent_step` telemetry with `response_type=text`.
- `workflow_summary` events are aggregate terminal-status events only. They omit token and cost fields so Production AI Platform does not double-count spend already reported by per-step `agent_step` events.

Deliverables:

- Decide whether structured generation is represented as `agent_step` metadata or a separate `structured_generation` operation.
- Add workflow summary telemetry only if it provides useful aggregate visibility without inflating cost totals.
- Document which AgentOps events are billing-estimate events versus aggregate summary events.
- Add tests for duplicate prevention and cost-total consistency.

Acceptance:

- Costs are not double-counted in the central dashboard.
- Summary events are clearly distinguishable from billable model-call events.
- Missing token/cost data is marked honestly as `unknown` or `unpriced`.

### Phase 45: Cross-Repository Automated Validation

Add validation that proves the AgentOps-to-platform integration without OpenAI, AWS, or deployments.

Deliverables:

- Platform schema tests for AgentOps-shaped events.
- AgentOps mocked receiver tests.
- AgentOps telemetry smoke script.
- Docker Compose config validation for both repos where applicable.
- Documentation for local validation commands.

Acceptance:

- Tests run without real OpenAI calls.
- Tests run without AWS or Terraform.
- Mocked platform failures do not break AgentOps workflows.

### Phase 46: Browser End-To-End AgentOps Telemetry Demo

Verify the integration through local apps and the dashboard.

Deliverables:

- Local run instructions for Production AI Platform and AgentOps on non-conflicting ports.
- Browser checklist:
  - run or simulate an AgentOps workflow
  - open Production AI Platform dashboard
  - filter to `source_app=agentops`
  - inspect agent-step telemetry
- Screenshot capture guidance and redaction rules.
- Troubleshooting notes for ports, env vars, API keys, and unavailable services.

Acceptance:

- Browser validation proves AgentOps traffic appears in Production AI Platform.
- Demo does not require Terraform, AWS resources, or production deployment.
- Screenshots avoid secrets, prompts, outputs, workflow JSON, tool payloads, and sensitive content.

Phase 46 implementation notes:

- Use `scripts/send_agentops_browser_demo_event.py` for the automated local browser proof path.
- Use [agentops-browser-telemetry-demo.md](../agentops-browser-telemetry-demo.md) for the dashboard checklist, AgentOps port guidance, screenshot rules, and troubleshooting notes.
- Use the real AgentOps smoke sender, `S:\github-repos\agentops-workflow-platform\scripts\send_platform_telemetry_smoke.py`, only after the platform API is running and seeded.
- Avoid real AgentOps workflow runs unless provider credentials and quota usage are intentional.

### Phase 47: AgentOps Integration Closeout

Finalize documentation and portfolio wording for the second connected client app.

Deliverables:

- Final AgentOps integration docs.
- README update showing Proofbase and AgentOps as connected client apps.
- Runbook notes for AgentOps telemetry ingestion outages.
- Security notes for telemetry API keys and workflow payload redaction.
- Observability notes for interpreting AgentOps workflow/step telemetry.

Acceptance:

- Docs can honestly claim AgentOps telemetry is centralized in Production AI Platform.
- Docs do not claim Production AI Platform executes AgentOps workflows or owns AgentOps tool behavior.
- Telemetry outage behavior is documented as non-blocking.
- Proofbase and AgentOps are described as distinct connected client apps with different domains.

Phase 47 implementation notes:

- The final connection summary lives in [agentops-integration.md](../agentops-integration.md).
- Runbook, security, observability, architecture, portfolio, and README docs now describe AgentOps as a connected telemetry client while preserving the workflow boundary.
- Proofbase remains the RAG/product integration; AgentOps remains the workflow/orchestration integration.

## Validation Baseline

Run these checks as the AgentOps phases are implemented:

```powershell
cd S:\github-repos\production-ai-platform
.\.venv\Scripts\python -m pytest apps/api/tests/test_proofbase_telemetry_contract.py -vv
.\.venv\Scripts\python scripts\validate_proofbase_telemetry_contract.py
docker compose config
```

AgentOps-specific validation commands:

```powershell
.\.venv\Scripts\python scripts\validate_agentops_telemetry_contract.py
.\.venv\Scripts\python -m pytest apps/api/tests/test_agentops_telemetry_contract.py apps/api/tests/test_external_telemetry.py -vv
.\.venv\Scripts\python scripts\send_agentops_browser_demo_event.py
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe scripts\test_phase45_mocked_platform_receiver.py
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe scripts\send_platform_telemetry_smoke.py
```

## Scope Boundary

Do not implement AgentOps execution, workflow orchestration, tool behavior, prompt engineering, or generated-output inspection inside Production AI Platform.

Production AI Platform should centralize operational telemetry only:

- source app
- operation type
- model/provider
- status/error
- latency
- tokens
- estimated cost
- safe workflow/agent-step metadata

AgentOps should continue to own:

- workflow definitions
- agent planning
- tool execution
- prompts
- structured outputs
- local run state
- workflow-specific cost records
