# Local Portfolio Stack

This runbook starts the three portfolio applications together on one Windows development machine:

| Application | Web | API | Database |
| --- | ---: | ---: | ---: |
| Production AI Platform | `http://localhost:3000` | `http://localhost:8000` | PostgreSQL `55432`, Redis `56379` |
| Proofbase | `http://localhost:3001` | `http://localhost:8001` | PostgreSQL `5432` |
| AgentOps Workflow Platform | `http://127.0.0.1:3002` | `http://127.0.0.1:8002` | PostgreSQL `55433` |

The platform now uses Java and automatically migrates/seeds its new local volume. Its default dashboard is an isolated read-only fixture; real ingested usage needs [OIDC/project grants](java-operator-security.md). The other apps retain their own implementations. See [Java cutover](java-runtime-cutover.md) before using historical browser verification instructions below.

Run the applications in this order so Proofbase and AgentOps can send telemetry to Production AI Platform.

## Prerequisites

- Docker Desktop is running.
- Java 21 (native API work), Python 3.12, Node.js 24 LTS, `pnpm`, and `uv` are installed.
- The repositories exist at:
  - `S:\github-repos\production-ai-platform`
  - `S:\github-repos\enterprise-knowledge-agent`
  - `S:\github-repos\agentops-workflow-platform`
- Real OpenAI credentials remain only in each repository's ignored `.env` file or the current terminal environment.

The deterministic Production AI Platform and AgentOps demo paths do not call OpenAI. Proofbase corpus ingestion and real Proofbase or AgentOps AI requests can consume OpenAI quota.

## First-Time Setup

### Production AI Platform

```powershell
cd S:\github-repos\production-ai-platform

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
}
```

### Proofbase

Do not overwrite an existing `.env`; it may contain a local OpenAI key.

```powershell
cd S:\github-repos\enterprise-knowledge-agent

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
}
```

For real Proofbase queries or first-time corpus ingestion, set `OPENAI_API_KEY` in the ignored Proofbase `.env` before starting Compose. Keep the value out of commands, screenshots, logs, and commits.

### AgentOps

```powershell
cd S:\github-repos\agentops-workflow-platform

pnpm install

cd apps\api
uv sync
cd ..\..

docker volume create agentops-local-data

docker run -d `
  --name agentops-postgres `
  -e POSTGRES_DB=agentops `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -p 55433:5432 `
  -v agentops-local-data:/var/lib/postgresql/data `
  postgres:16
```

If port `55433` is occupied by the disposable `agentops-verify-postgres` container, stop it before creating the persistent container:

```powershell
docker stop agentops-verify-postgres
```

## Start All Three Applications

### Terminal 1: Production AI Platform

```powershell
cd S:\github-repos\production-ai-platform

docker compose up -d --build --wait

docker compose ps
curl.exe --fail http://localhost:8000/health/ready
```

Open `http://localhost:3000`.

### Terminal 2: Proofbase

The environment variables below keep Proofbase away from the Production AI Platform ports.

```powershell
cd S:\github-repos\enterprise-knowledge-agent

$env:API_PORT="8001"
$env:WEB_PORT="3001"
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8001"

docker compose up -d --build postgres api web
docker compose run --rm api python scripts/setup_db.py

docker compose ps
curl.exe --fail http://localhost:8001/health
curl.exe --fail http://localhost:8001/ready
```

Open `http://localhost:3001`.

Proofbase schema setup seeds the Northstar project, departments, demo users, and prompt metadata. If the Proofbase database has no indexed documents, run this separately only when OpenAI usage is intentional:

```powershell
cd S:\github-repos\enterprise-knowledge-agent

$env:API_PORT="8001"
$env:WEB_PORT="3001"
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8001"

docker compose run --rm api python scripts/ingest_markdown.py `
  --apply-schema `
  --chunking-strategy section_based
```

That ingestion command calls the OpenAI embeddings API.

### Terminal 3: AgentOps API

Keep this terminal open after Uvicorn starts.

```powershell
cd S:\github-repos\agentops-workflow-platform\apps\api

docker start agentops-postgres

$env:DATABASE_URL="postgresql://postgres:postgres@localhost:55433/agentops"
$env:AGENTOPS_TELEMETRY_ENABLED="true"
$env:AGENTOPS_TELEMETRY_ENDPOINT="http://localhost:8000/v1/usage/llm-events"
$env:AGENTOPS_TELEMETRY_API_KEY="agentops-local-placeholder-key-not-a-secret"
$env:AGENTOPS_TELEMETRY_TIMEOUT_SECONDS="2"
$env:AGENTOPS_TELEMETRY_MAX_METADATA_BYTES="2048"
$env:AGENTOPS_TELEMETRY_REDACT_CONTENT="true"

.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m src.seed_demo_dataset

.\.venv\Scripts\python.exe -m uvicorn src.main:app `
  --reload `
  --host 127.0.0.1 `
  --port 8002
```

The AgentOps seed is idempotent and does not call OpenAI. It populates workflow runs, evaluation results, uploaded inputs, and agent steps.

### Terminal 4: AgentOps Web

Keep this terminal open.

```powershell
cd S:\github-repos\agentops-workflow-platform

$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8002"

pnpm --dir apps\web dev `
  --hostname 127.0.0.1 `
  --port 3002
```

Open `http://127.0.0.1:3002/demo`.

## Verify The Running Stack

```powershell
curl.exe --fail http://localhost:8000/health/ready
curl.exe --fail http://localhost:8001/health
curl.exe --fail http://localhost:8001/ready
curl.exe --fail http://127.0.0.1:8002/health
curl.exe --fail http://127.0.0.1:8002/ready
```

Expected application checks:

- Production AI Platform loads at `http://localhost:3000`.
- Proofbase loads at `http://localhost:3001` and shows the Northstar project.
- AgentOps loads at `http://127.0.0.1:3002/demo` and shows seeded workflow and evaluation counts.

## Verify Cross-Application Telemetry

### Safe Proofbase-shaped Event

This sender does not make a real Proofbase query or call OpenAI.

```powershell
cd S:\github-repos\production-ai-platform
.\.venv\Scripts\python.exe scripts\send_proofbase_browser_demo_event.py
```

### Safe AgentOps-shaped Event

```powershell
cd S:\github-repos\agentops-workflow-platform

$env:AGENTOPS_TELEMETRY_ENDPOINT="http://localhost:8000/v1/usage/llm-events"
$env:AGENTOPS_TELEMETRY_API_KEY="agentops-local-placeholder-key-not-a-secret"

.\apps\api\.venv\Scripts\python.exe scripts\send_platform_telemetry_smoke.py
```

Open `http://localhost:3000` and filter **Source App** to `proofbase` or `agentops`.

## Real AI Workflows

Proofbase obtains `OPENAI_API_KEY` from its ignored `.env` through the Compose secret. AgentOps real workflows require the key in the AgentOps API terminal before Uvicorn starts:

```powershell
$env:OPENAI_API_KEY="<set-locally-and-never-commit>"
```

Do not use a real key for deterministic demo seeding or telemetry smoke checks.

## Stop All Three Applications

First press `Ctrl+C` in the AgentOps API and AgentOps web terminals.

```powershell
docker stop agentops-postgres

cd S:\github-repos\enterprise-knowledge-agent
docker compose down

cd S:\github-repos\production-ai-platform
docker compose down
```

These commands preserve named volumes and local demo data. Do not add `--volumes` unless losing the local databases is intentional.

## Restart After First-Time Setup

For later sessions, run only the four terminal blocks under **Start All Three Applications**. The migration and seed commands are safe to repeat.

## Troubleshooting

- A dashboard shows zeros: rerun that application's seed or setup command and refresh the page.
- AgentOps API is ready but the UI shows zeros: confirm the web terminal uses `NEXT_PUBLIC_API_URL=http://127.0.0.1:8002`, rerun `python -m src.seed_demo_dataset`, and refresh.
- Port `5432` is unavailable: Proofbase owns that host port in this layout. Stop the conflicting local PostgreSQL service or container.
- Port `55433` is unavailable: stop an old AgentOps verification container before starting `agentops-postgres`.
- Proofbase cannot make real queries: confirm its ignored `.env` contains a valid OpenAI key and that corpus ingestion completed intentionally.
- Telemetry returns `401`: rerun the Production AI Platform seed command to restore the local placeholder application keys.
- A Docker-hosted client cannot reach the platform: use `http://host.docker.internal:8000` from inside Docker, not `localhost:8000`.
