# AgentOps Browser Telemetry Demo

This guide verifies the AgentOps-to-Production AI Platform telemetry path with local services only. It does not run Terraform, create AWS resources, deploy anything, or require production credentials.

## Local Run

From `S:\github-repos\production-ai-platform`:

```powershell
docker compose up -d postgres redis api web
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_dev_data
```

Open the platform dashboard:

```text
http://localhost:3000
```

Use `localhost`, not `127.0.0.1`, for the Next.js dev dashboard. Next.js may block dev resources when the page host does not match the dev server host.

## Safe Local AgentOps Event

Send one local AgentOps-shaped event to the running platform API:

```powershell
.\.venv\Scripts\python scripts\send_agentops_browser_demo_event.py
```

The script uses placeholder-only local data:

- source app: `agentops`
- operation: `agent_step`
- project: `AgentOps Workflow Platform`
- application: `AgentOps Workflow Platform`
- request id prefix: `ext_`
- no prompt text, generated output, workflow input/output JSON, tool arguments, tool results, provider payload, API key, provider credential, or user/customer data

By default, the script generates a unique event id so it can be rerun during demos.

## Browser Checklist

1. Open `http://localhost:3000`.
2. Confirm the dashboard loads and shows `http://localhost:8000` as the API base URL.
3. In **Source App**, select `agentops`.
4. Confirm the summary cards show one AgentOps request for the demo event.
5. Confirm **Recent Requests** shows:
   - scope `AgentOps Workflow Platform / AgentOps Workflow Platform`
   - source `agentops`
   - operation `Agent Step`
   - model `gpt-4.1-mini`
   - estimated cost `$0.000102`
6. Open the request detail panel and confirm:
   - telemetry is reported by `agentops`
   - operation is `Agent Step`
   - tokens are `128 in / 32 out`
   - cost is `$0.000102`
   - the external event id begins with `evt_phase46_agentops_browser_demo`
   - the external request id begins with `agentops_step_phase46_browser_demo`
7. Confirm **Recent Failures** says no matching failures for this success-only demo.

## Full AgentOps Workflow Path

To run a real AgentOps local workflow on non-conflicting ports while the platform owns ports 3000 and 8000:

```powershell
cd S:\github-repos\agentops-workflow-platform
$env:API_PORT="8001"
$env:WEB_PORT="3001"
$env:AGENTOPS_TELEMETRY_ENABLED="true"
$env:AGENTOPS_TELEMETRY_ENDPOINT="http://localhost:8000/v1/usage/llm-events"
$env:AGENTOPS_TELEMETRY_API_KEY="agentops-local-placeholder-key-not-a-secret"
$env:AGENTOPS_TELEMETRY_REDACT_CONTENT="true"
```

Then start AgentOps with its normal local development command and open:

```text
http://localhost:3001
```

Run a short synthetic workflow using demo-only content. This path can call OpenAI from AgentOps if its local `OPENAI_API_KEY` is configured, so use it only when you intentionally want to spend provider quota. The automated Phase 46 validation uses the safe local event sender above instead.

AgentOps also includes a smoke sender that can post one safe event through its telemetry client after the platform API is running and seeded:

```powershell
cd S:\github-repos\agentops-workflow-platform
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe scripts\send_platform_telemetry_smoke.py
```

## Screenshot Rules

Capture only local or staging demo data. Screenshots are acceptable when they show aggregate counts, short request ids, project/app names, source app, operation, model, latency, tokens, and estimated cost.

Do not capture or commit screenshots that show:

- API keys or provider credentials
- account IDs, real domains, database URLs, or Redis URLs
- full prompts, agent instructions, or generated outputs
- workflow input/output JSON
- tool arguments, tool results, or provider payloads
- customer, employee, or incident data

Store approved screenshots under `docs/assets/screenshots/` only after reviewing them for redaction.

## Troubleshooting

- Platform dashboard keeps loading: open `http://localhost:3000` instead of `http://127.0.0.1:3000`, then refresh.
- Platform API is unavailable: check `docker compose ps` and `docker compose logs api`.
- Migrations fail before the dashboard has data: rerun `docker compose exec api alembic upgrade head` and confirm the Alembic revision id fits the default version table.
- Telemetry POST returns `401`: reseed local demo data or use the placeholder AgentOps key from `.env.example`.
- AgentOps ports conflict with the platform: run AgentOps on `API_PORT=8001` and `WEB_PORT=3001`.
- Real AgentOps workflow fails without an OpenAI key: use the safe local event sender for platform browser validation, or intentionally configure AgentOps provider credentials for a real workflow demo.
- AgentOps runs inside Docker but the platform API runs on the host: set `AGENTOPS_TELEMETRY_ENDPOINT=http://host.docker.internal:8000/v1/usage/llm-events`.
