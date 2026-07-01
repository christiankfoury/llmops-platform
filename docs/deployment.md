# Deployment

## Environments

The project targets four environments:

- local
- dev
- staging
- prod

## Local deployment

Implemented local stack:

```text
Docker Compose:
- API
- Web
- PostgreSQL
- Redis
```

Start the full stack:

```bash
docker compose up --build
```

The same command is available as:

```bash
make local-up
```

Local service URLs:

- Web dashboard: `http://localhost:3000`
- API health: `http://localhost:8000/health`
- API readiness: `http://localhost:8000/health/ready`
- PostgreSQL host port: `55432`
- Redis host port: `56379`

The web dashboard reads the API directly through `NEXT_PUBLIC_API_BASE_URL` and renders usage, recent requests, failures, prompt versions, and model routes.

Stop containers:

```bash
make local-down
```

Run database migrations and seed local development data after the stack is running:

```bash
make api-migrate
make api-seed
```

## Production image builds

Phase 9 adds production Dockerfiles for the API and web dashboard while keeping the development Dockerfiles used by Docker Compose.

Build both production images:

```bash
make docker-build-prod
```

Equivalent direct commands:

```bash
docker build -f apps/api/Dockerfile -t production-ai-platform-api:prod apps/api
docker build -f apps/web/Dockerfile -t production-ai-platform-web:prod apps/web
```

The API production image:

- installs runtime dependencies from `requirements.prod.txt`
- excludes test and formatting tools from the runtime dependency set
- runs as non-root user `10001`
- exposes port `8000`
- defines a container health check against `/health/live`
- reads `ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL`, and `API_CORS_ORIGINS` from environment variables

The web production image:

- uses a multi-stage Next.js standalone build
- runs as non-root user `10001`
- exposes port `3000`
- defines a container health check against `/`
- reads `API_BASE_URL` or `NEXT_PUBLIC_API_BASE_URL` at runtime through `/api/runtime-config`

Local production-image smoke test:

```bash
docker run --rm -p 18000:8000 production-ai-platform-api:prod
docker run --rm -p 13000:3000 -e API_BASE_URL=http://host.docker.internal:8000 production-ai-platform-web:prod
```

Those commands start containers locally only. Cloud registry publishing and Kubernetes deployment are later-phase work.

Smoke-test the local gateway with the seeded placeholder key:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"hello from local development"}'
```

The local seed key is intentionally non-secret placeholder data and is stored as a hash.

The mock provider supports local failure-path checks:

- `"[simulate_failure]"` returns HTTP 502 and records `provider_error`.
- `"[simulate_timeout]"` returns HTTP 504 and records `provider_timeout`.

Check aggregate usage after sending gateway requests:

```bash
curl http://localhost:8000/v1/usage/summary
```

Inspect local operator configuration:

```bash
curl http://localhost:8000/v1/admin/prompt-versions
curl http://localhost:8000/v1/admin/model-routes
```

Admin create/update calls accept `X-Actor-ID` and write audit logs. These endpoints are intentionally not production-hardened yet; admin authentication and stronger access controls are later-phase work.

Local environment examples live in:

- `.env.example`
- `apps/api/.env.example`
- `apps/web/.env.example`

These files use placeholder development values only. Real provider keys, cloud account IDs, and production secrets must not be committed.

## Dev deployment

Dev should deploy automatically from the main branch.

Expected flow:

1. CI validates code.
2. Images are built.
3. Images are pushed to ECR.
4. Helm upgrades dev release.
5. Smoke test runs.

Terraform foundation code for dev, staging, and prod lives under `infra/terraform/environments`. Phase 11 supports safe local `fmt`, `init -backend=false`, and `validate` checks only. Creating AWS resources with `terraform apply` is an explicit approval gate.

See `docs/terraform.md` for backend configuration, AWS credential expectations, and validation commands.

Phase 12 adds EKS Terraform code and Kubernetes provider wiring. It remains code-only until an explicit approval gate allows AWS resource creation.

Phase 13 adds managed PostgreSQL and Redis Terraform code. These resources are private, encrypted, and backed up by default, but they are still not created until an approved `terraform apply`.

## Kubernetes manifests

Phase 14 adds raw Kubernetes manifests under `infra/k8s`.

Render the base manifests:

```bash
kubectl kustomize infra/k8s/base
```

Render environment overlays:

```bash
kubectl kustomize infra/k8s/overlays/dev
kubectl kustomize infra/k8s/overlays/staging
kubectl kustomize infra/k8s/overlays/prod
```

The manifests include:

- namespace per environment
- API and web service accounts
- API and web ConfigMaps
- API and web Deployments
- API and web ClusterIP Services
- ALB-oriented Ingress
- liveness and readiness probes
- resource requests and limits
- non-root pod and container security contexts
- secret references for `DATABASE_URL` and `REDIS_URL`

The referenced `ai-platform-runtime-secrets` Secret is intentionally not committed. Later External Secrets work will bind AWS Secrets Manager values into Kubernetes without plaintext manifests.

These manifests are raw Kubernetes foundations. Helm packaging, release values, External Secrets, HPA, PDB, and NetworkPolicies are later phases.

## Staging deployment

Staging should be manually triggered.

Expected flow:

1. Select image tag or commit SHA.
2. Deploy with staging values.
3. Run smoke test.
4. Validate dashboards and logs.

## Production deployment

Production requires approval.

Expected flow:

1. Confirm release notes.
2. Confirm staging validation.
3. Approve production workflow.
4. Deploy with production values.
5. Run smoke test.
6. Monitor dashboards.

## Rollback

Rollback is handled through Helm release history and a dedicated GitHub Actions rollback workflow.

See `docs/runbook.md` and `docs/incident-response.md`.
