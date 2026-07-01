# Production AI Platform / LLMOps Infrastructure Platform

A production-grade AI platform portfolio project for DevOps, cloud, backend, full-stack, and LLMOps roles.

The application is intentionally scoped: a lightweight LLM gateway and usage dashboard. The main value is the production infrastructure around it: Kubernetes, Terraform, Helm, CI/CD, observability, secrets, reliability, rollback, and cost controls.

## Portfolio relationship

This project complements **Proofbase**, the permission-aware enterprise RAG application. Proofbase demonstrates the AI product layer: document ingestion, retrieval quality, citations, permissions, memory safety, and benchmark-driven answer evaluation.

Production AI Platform demonstrates the operating layer: centralized LLM access, API keys, prompt and model routing, usage tracking, cost and latency monitoring, CI/CD, Kubernetes, Terraform, observability, secrets, rollback, and runbooks.

A future integration could make Proofbase a client application of this platform, sending model requests through the LLM gateway so cost, latency, traces, and model routing are managed centrally.

## Target Portfolio Claim

> Built a production-grade AI platform on AWS using Kubernetes, Terraform, Helm, GitHub Actions, Prometheus, Grafana, Loki, OpenTelemetry, managed PostgreSQL, Redis, external secret management, staged deployments, rollback workflows, request tracing, cost monitoring, and reliability runbooks.

## What this project demonstrates

- Cloud infrastructure with Terraform
- Kubernetes deployment on AWS EKS
- Helm packaging
- CI/CD with GitHub Actions
- Staged environments: dev, staging, prod
- Production Docker images
- Managed PostgreSQL and Redis
- Secret management with AWS Secrets Manager and External Secrets
- Prometheus metrics
- Grafana dashboards
- Loki centralized logs
- OpenTelemetry tracing
- API gateway request tracking
- LLM cost and latency tracking
- Rollback workflows
- Incident response runbooks
- Cost analysis and controls

## Core app

The platform includes:

- LLM gateway API
- API keys per app/project
- Prompt versioning
- Model routing
- Request logging
- Cost tracking
- Latency tracking
- Failure tracking
- Usage dashboard
- Cost/error/latency dashboard

## Local development

Phase 2 adds the local development foundation:

- FastAPI service in `apps/api`
- Next.js dashboard in `apps/web`
- Docker Compose stack with API, web, PostgreSQL, and Redis
- Health endpoints at `GET /health`, `GET /health/live`, and `GET /health/ready`

Start the local stack:

```bash
docker compose up --build
```

Then open:

- Web dashboard: `http://localhost:3000`
- API health: `http://localhost:8000/health`

The dashboard shows real API data: usage totals, estimated cost, average latency, recent requests, recent failures, prompt versions, and model routes.

After migrations and seed data are loaded, the local gateway can be smoke-tested with the placeholder seed key:

```bash
curl -X POST http://localhost:8000/v1/gateway/completions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-placeholder-key-not-a-secret" \
  -d '{"input":"hello from local development"}'
```

The placeholder key is for local seeded data only and is stored in PostgreSQL as a hash.

Successful gateway responses include a request ID, selected provider/model, latency, estimated token usage, and estimated cost. Local failure handling can be smoke-tested with `"[simulate_failure]"` for a provider error or `"[simulate_timeout]"` for a provider timeout.

Usage summary:

```bash
curl http://localhost:8000/v1/usage/summary
```

Local operator configuration endpoints are available for prompt versions and model routes:

```bash
curl http://localhost:8000/v1/admin/prompt-versions
curl http://localhost:8000/v1/admin/model-routes
```

Create/update operations accept an optional `X-Actor-ID` header and write audit log records. These admin endpoints are local foundations; hardened admin auth is a later security phase.

Useful local commands:

```bash
make local-up
make local-down
make api-migrate
make api-seed
make api-test
make web-lint
make web-typecheck
make web-test
make check
make docker-build-prod
```

GitHub Actions CI runs the same backend/frontend quality checks, production image builds, dependency audit gates, image scans, and infrastructure placeholders on pushes to `main`.

The dev CD workflow builds API and web images, pushes immutable commit-SHA tags to ECR, deploys the Helm release to the dev EKS namespace, checks rollout status, and smoke-tests the API and dashboard. Automatic main-branch deployment is guarded by explicit repository variables so the workflow can be reviewed before it mutates a real AWS environment. Staging and production releases are manual promotion workflows; production binds to a protected GitHub Environment approval gate. Rollback is a manual Helm workflow with selected revision, rollout checks, smoke tests, and production approval.

OpenTelemetry tracing is available in the API and disabled by default. When enabled, the gateway emits spans for request handling, authentication, prompt lookup, model routing, provider calls, database writes, and response serialization, with request IDs and trace IDs in structured request logs.

Configuration is documented in `.env.example`, `apps/api/.env.example`, and `apps/web/.env.example`. These examples use local-only placeholder values and do not contain real credentials.

## Infrastructure Roadmap

The infrastructure roadmap is the center of the project:

- Local development with Docker Compose, PostgreSQL, Redis, API, and web dashboard
- AWS foundation with Terraform modules for network, registry, IAM, secrets, EKS, RDS PostgreSQL, and ElastiCache Redis
- Kubernetes deployment through raw manifests first, then a reusable Helm chart
- GitHub Actions CI/CD with staged dev, staging, production, and rollback workflows
- Observability through OpenTelemetry traces, Prometheus metrics, Grafana dashboards, Loki logs, and alerting runbooks
- Security and reliability hardening through External Secrets, workload identity, NetworkPolicies, probes, resource limits, HPA, PDB, backups, and incident response docs

## Scope boundary

This project does not implement advanced RAG, vector retrieval, citation validation, document ingestion, or benchmark-driven answer evaluation. Those capabilities belong in Proofbase. This repo stays focused on production AI platform operations and LLMOps infrastructure.

## Target architecture

```text
Client Apps
   |
   v
Ingress / TLS
   |
   v
LLM Gateway API  ---> PostgreSQL
   |                  Redis
   |
   v
LLM Provider / Mock Provider

Observability:
API -> OpenTelemetry -> Collector
API -> Prometheus metrics
API -> JSON logs -> Loki
Grafana -> Prometheus/Loki
```

## Repository structure

```text
apps/
  api/
  web/

infra/
  terraform/
    environments/
      dev/
      staging/
      prod/
    modules/
      network/
      registry/
      cluster/
      database/
      redis/
      secrets/
      iam/
      monitoring/
  helm/
    ai-platform/
      templates/
  k8s/
    base/
    overlays/
      dev/
      staging/
      prod/

.github/
  workflows/

docs/
```

## Roadmap

See `phases.md`. The roadmap is intentionally phase-based so each increment can be reviewed, validated, committed, and explained as portfolio evidence.

## Codex workflow

See `AGENTS.md`.

## Progress

See `phases-progress.md`.

## Documentation

- `PROJECT_SPEC.md`
- `docs/architecture.md`
- `docs/deployment.md`
- `docs/testing.md`
- `docs/terraform.md`
- `docs/runbook.md`
- `docs/incident-response.md`
- `docs/observability.md`
- `docs/cost-analysis.md`
- `docs/security-baseline.md`
- `docs/portfolio-demo-plan.md`

## Status

Phases 1-19 are complete, covering the local app, database foundation, gateway path, dashboard, quality baseline, production Docker images, CI pipeline, Terraform AWS foundation, EKS cluster layer, managed data services, base Kubernetes manifests, Helm chart, guarded dev deployment workflow, manual staging/approved production release workflows, Helm rollback automation, and OpenTelemetry tracing. Phase 20 adds Prometheus metrics.
