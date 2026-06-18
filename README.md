# Production AI Platform / LLMOps Infrastructure Platform

A production-grade AI platform built to demonstrate DevOps, cloud, backend, and LLMOps skills.

The app is a lightweight LLM gateway and dashboard. The infrastructure is the main portfolio showcase.

## Portfolio claim

> Production AI Platform deployed on Kubernetes with Terraform-managed AWS infrastructure, Helm-based releases, GitHub Actions CI/CD, Prometheus/Grafana observability, Loki logs, OpenTelemetry tracing, secret management, staged environments, rollback support, and cost/latency monitoring.

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
  helm/
  k8s/

.github/
  workflows/

docs/
```

## Roadmap

See `phases.md`.

## Codex workflow

See `AGENTS.md`.

## Progress

See `phases-progress.md`.

## Documentation

- `PROJECT_SPEC.md`
- `docs/architecture.md`
- `docs/deployment.md`
- `docs/runbook.md`
- `docs/incident-response.md`
- `docs/cost-analysis.md`
- `docs/security-baseline.md`
- `docs/portfolio-demo-plan.md`

## Status

Brand-new project. Phase 1 is the starting point.
