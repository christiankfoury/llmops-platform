# Testing

Phase 8 adds a local quality baseline for backend and frontend work.

Run the full local check set:

```bash
make check
```

The Makefile defaults to the local Windows virtualenv path `.venv/Scripts/python`. On macOS/Linux, run with an override such as:

```bash
make check API_PYTHON=.venv/bin/python
```

Backend checks:

```bash
make api-lint
make api-format-check
make api-test
```

Frontend checks:

```bash
make web-lint
make web-typecheck
make web-test
```

Docker and migration checks remain phase-specific until CI is introduced:

```bash
docker compose build api web
docker compose exec -T api alembic check
```

The frontend dependency audit currently passes the high/critical gate with:

```bash
npm audit --audit-level=high
```

The Phase 48 review refreshed Next.js and eslint-config-next to 16.3.4 and updated compatible transitive dependencies. On 2026-09-06, npm audit reported zero vulnerabilities; lint, type checks, six frontend tests, and the production build passed locally. Re-run the audit on each release because advisory data changes over time.

## CI checks

Phase 10 adds `.github/workflows/ci.yml` for pushes and pull requests targeting `main`.

The workflow runs:

- backend Ruff lint and format checks
- backend Alembic migration plus pytest against a PostgreSQL service
- deterministic Python migration contract drift check and required PostgreSQL telemetry fixture lifecycle
- frontend lint, typecheck, Vitest, and high/critical npm audit gate
- production API and web Docker image builds
- Trivy high/critical image scans
- blocking Python dependency scanning with `pip-audit --strict`
- repository-level Trivy filesystem scan for high/critical vulnerability, config, and secret findings
- Terraform formatting and Helm lint checks for the implemented infrastructure/chart files

Phase 25 makes the Python dependency scan blocking. The blocking supply-chain gates are frontend high/critical npm audit, Python production dependency audit, high/critical container image scans, and repository-level Trivy filesystem scanning.

See [ci-cd.md](ci-cd.md) for a fuller explanation of the GitHub Actions jobs, the actions used by the workflow, and how CI differs from local Docker Compose.

Phase 49 adds the [Java migration contract](java-migration-contract.md). Run `python scripts/export_backend_contract.py --check` to detect drift without changing files. Its static export uses no database or provider. The PostgreSQL lifecycle regression must run in CI (`REQUIRE_DATABASE_TESTS=true`); local skips must be reported separately from passing tests.

## Smoke Load

Phase 26 adds a small gateway smoke load script. After local migrations and seed data are available, run:

```bash
python scripts/smoke_load.py --base-url http://localhost:8000 --requests 20 --concurrency 4
```

This is a resilience smoke check, not a benchmark. Use it to verify that the gateway handles modest concurrent traffic, emits request metrics, and keeps failures visible during local demos.

## Proofbase Telemetry Validation

Phase 38 adds cross-repository validation for the Proofbase telemetry integration. These checks do not call OpenAI, create AWS resources, run Terraform, or deploy either application.

From `S:\github-repos\production-ai-platform`:

```powershell
.\.venv\Scripts\python scripts\validate_proofbase_telemetry_contract.py
.\.venv\Scripts\python -m pytest apps/api/tests/test_proofbase_telemetry_contract.py -vv
docker compose config
```

From `S:\github-repos\enterprise-knowledge-agent`:

```powershell
.\.venv\Scripts\python scripts\test_platform_telemetry_client.py
.\.venv\Scripts\python scripts\test_phase36_query_telemetry.py
.\.venv\Scripts\python scripts\test_phase37_auxiliary_telemetry.py
.\.venv\Scripts\python scripts\test_phase38_mocked_platform_receiver.py
docker compose config
```

What these checks prove:

- Proofbase-shaped telemetry events validate against the platform schema for `rag_query`, `rag_query_stream`, `markdown_cleanup`, `query_decomposition`, and `embedding_generation`.
- Sensitive metadata such as full questions is rejected by the platform schema.
- Proofbase telemetry submission can be tested against a mocked receiver with no network call.
- Receiver failures return `False` and do not raise into user-facing workflows.
- Docker Compose files parse locally without starting containers.

## Proofbase Browser Telemetry Demo

Phase 39 adds a local browser validation path for the Proofbase dashboard connection. Start the platform stack, migrate, seed, send one safe Proofbase-shaped event, and inspect it in the web dashboard:

```powershell
docker compose up -d postgres redis api web
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_dev_data
.\.venv\Scripts\python scripts\send_proofbase_browser_demo_event.py
```

Then open `http://localhost:3000`, filter **Source App** to `proofbase`, and confirm the dashboard shows the `Proofbase / Enterprise Knowledge Agent` request.

See [proofbase-browser-telemetry-demo.md](proofbase-browser-telemetry-demo.md) for the full browser checklist, Proofbase port guidance, screenshot rules, and troubleshooting notes.

## AgentOps Telemetry Contract Validation

Phase 41 adds platform-side contract checks for the AgentOps Workflow Platform integration. These checks do not call OpenAI, create AWS resources, run Terraform, deploy Kubernetes resources, or require AgentOps to be running.

From `S:\github-repos\production-ai-platform`:

```powershell
.\.venv\Scripts\python scripts\validate_agentops_telemetry_contract.py
.\.venv\Scripts\python -m pytest apps/api/tests/test_agentops_telemetry_contract.py apps/api/tests/test_proofbase_telemetry_contract.py -vv
```

What these checks prove:

- AgentOps-shaped telemetry events validate for `agent_step`, `structured_generation`, and `workflow_summary`.
- Existing Proofbase telemetry fixtures still validate against the shared external schema.
- Unsafe top-level fields such as workflow JSON, generated output, provider payloads, tool payloads, and API keys are rejected.
- Unsafe metadata fields such as raw prompts, input/output JSON, and tool results are rejected.

## AgentOps Cross-Repository Validation

Phase 45 adds no-cloud validation for the AgentOps-to-platform telemetry path. These checks do not call OpenAI, AWS, Terraform, Kubernetes, or a running Production AI Platform deployment.

From `S:\github-repos\production-ai-platform`:

```powershell
.\.venv\Scripts\python scripts\validate_agentops_telemetry_contract.py
.\.venv\Scripts\python -m pytest apps/api/tests/test_agentops_telemetry_contract.py apps/api/tests/test_external_telemetry.py -vv
docker compose config
```

From `S:\github-repos\agentops-workflow-platform`:

```powershell
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe scripts\test_phase45_mocked_platform_receiver.py
S:\github-repos\agentops-workflow-platform\apps\api\.venv\Scripts\python.exe -m pytest apps/api/tests/test_platform_telemetry.py apps/api/tests/test_cost_tracking.py apps/api/tests/test_workflow_state.py -vv
docker compose --env-file .env.example config
```

What these checks prove:

- Platform schema and ingestion accept AgentOps-shaped telemetry fixtures.
- AgentOps can submit agent-step and workflow-summary payloads to a mocked receiver without network calls.
- Mocked receiver failures return `False` and do not raise into AgentOps workflow code.
- Workflow summary events are accepted without creating central cost records.
- Docker Compose files parse locally without starting containers.

## AgentOps Browser Telemetry Demo

Phase 46 adds a local browser validation path for the AgentOps dashboard connection. Start the platform stack, migrate, seed, send one safe AgentOps-shaped event, and inspect it in the web dashboard:

```powershell
docker compose up -d postgres redis api web
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_dev_data
.\.venv\Scripts\python scripts\send_agentops_browser_demo_event.py
```

Then open `http://localhost:3000`, filter **Source App** to `agentops`, and confirm the dashboard shows the `AgentOps Workflow Platform / AgentOps Workflow Platform` request.

See [agentops-browser-telemetry-demo.md](agentops-browser-telemetry-demo.md) for the full browser checklist, AgentOps port guidance, screenshot rules, and troubleshooting notes.
