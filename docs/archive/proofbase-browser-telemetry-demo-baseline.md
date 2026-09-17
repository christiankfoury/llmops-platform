> Historical document. See the [current documentation](../README.md).

# Proofbase Browser Telemetry Demo

This guide verifies the Proofbase-to-Production AI Platform telemetry path with local services only. It does not run Terraform, create AWS resources, deploy anything, or require production credentials.

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

## Safe Local Proofbase Event

Send one local Proofbase-shaped event to the running platform API:

```powershell
.\.venv\Scripts\python scripts\send_proofbase_browser_demo_event.py
```

The script uses placeholder-only local data:

- source app: `proofbase`
- operation: `rag_query`
- project: `Proofbase`
- application: `Enterprise Knowledge Agent`
- request id prefix: `ext_`
- no full question, prompt, citation text, document text, retrieved chunks, provider payload, or secret

By default, the script generates a unique event id so it can be rerun during demos.

## Browser Checklist

1. Open `http://localhost:3000`.
2. Confirm the dashboard loads and shows `http://localhost:8000` as the API base URL.
3. In **Source App**, select `proofbase`.
4. Confirm the summary cards show one Proofbase request for the demo event.
5. Confirm **Recent Requests** shows:
   - scope `Proofbase / Enterprise Knowledge Agent`
   - source `proofbase`
   - operation `Rag Query`
   - model `gpt-4.1-mini`
   - estimated cost `$0.000046`
6. Confirm **Recent Failures** says no matching failures for this success-only demo.

## Full Proofbase Query Path

To run a real Proofbase browser query, start Proofbase on non-conflicting ports and enable telemetry in its local environment:

```powershell
cd S:\github-repos\enterprise-knowledge-agent
$env:API_PORT="8001"
$env:WEB_PORT="3001"
$env:PROOFBASE_TELEMETRY_ENABLED="true"
$env:PROOFBASE_TELEMETRY_ENDPOINT="http://host.docker.internal:8000/v1/usage/llm-events"
$env:PROOFBASE_TELEMETRY_API_KEY="proofbase-local-placeholder-key-not-a-secret"
docker compose up --build
```

Then open:

```text
http://localhost:3001
```

Send a short synthetic demo question that does not contain private data. This path can call OpenAI from Proofbase if its local `OPENAI_API_KEY` is configured, so use it only when you intentionally want to spend provider quota. The automated Phase 39 validation used the safe local event sender above instead.

## Screenshot Rules

Capture only local or staging demo data. Screenshots are acceptable when they show aggregate counts, short request ids, project/app names, source app, operation, model, latency, and estimated cost.

Do not capture or commit screenshots that show:

- API keys or provider credentials
- account IDs, real domains, database URLs, or Redis URLs
- full questions or prompts
- retrieved chunks, citation text, document text, or uploaded content
- customer, employee, or incident data

Store approved screenshots under `docs/assets/screenshots/` only after reviewing them for redaction.

## Troubleshooting

- Platform dashboard keeps loading: open `http://localhost:3000` instead of `http://127.0.0.1:3000`, then refresh.
- Platform API is unavailable: check `docker compose ps` and `docker compose logs api`.
- Migrations fail before the dashboard has data: rerun `docker compose exec api alembic upgrade head` and confirm the Alembic revision id fits the default version table.
- Telemetry POST returns `401`: reseed local demo data or use the placeholder Proofbase key from `.env.example`.
- Proofbase ports conflict with the platform: run Proofbase on `API_PORT=8001` and `WEB_PORT=3001`.
- Real Proofbase query fails without an OpenAI key: use the safe local event sender for platform browser validation, or intentionally configure Proofbase provider credentials for a real query demo.
