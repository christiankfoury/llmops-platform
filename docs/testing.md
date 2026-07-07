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

npm still reports a moderate Next/PostCSS advisory where the automatic fix is a breaking downgrade. Keep this visible until the Next stable line has a non-breaking patched path.

## CI checks

Phase 10 adds `.github/workflows/ci.yml` for pushes and pull requests targeting `main`.

The workflow runs:

- backend Ruff lint and format checks
- backend Alembic migration plus pytest against a PostgreSQL service
- frontend lint, typecheck, Vitest, and high/critical npm audit gate
- production API and web Docker image builds
- Trivy high/critical image scans
- blocking Python dependency scanning with `pip-audit --strict`
- repository-level Trivy filesystem scan for high/critical vulnerability, config, and secret findings
- Terraform formatting and Helm lint checks for the implemented infrastructure/chart files

Phase 25 makes the Python dependency scan blocking. The blocking supply-chain gates are frontend high/critical npm audit, Python production dependency audit, high/critical container image scans, and repository-level Trivy filesystem scanning.

See [ci-cd.md](ci-cd.md) for a fuller explanation of the GitHub Actions jobs, the actions used by the workflow, and how CI differs from local Docker Compose.

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
