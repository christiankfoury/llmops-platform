# Architecture

## Overview

This project is a production-style LLMOps platform.

The product surface is intentionally small:

- Gateway API
- Dashboard
- Database
- Redis
- Observability stack

The infrastructure surface is intentionally serious:

- Terraform-managed AWS infrastructure
- EKS Kubernetes cluster
- Helm chart deployment
- Staged environments
- CI/CD
- Secrets
- Observability
- Rollback
- Runbooks
- Cost controls

The architecture is designed to support a recruiter-facing claim about production operations. The LLM gateway is the workload; the surrounding platform is the main artifact.

## Logical architecture

```text
Users / Client Apps
        |
        v
    Ingress
        |
        v
+-------------------+
| LLM Gateway API   |
+-------------------+
 |        |        |
 |        |        +--> Mock/Real LLM Provider
 |        |
 |        +----------> Redis
 |
 +-------------------> PostgreSQL

API emits:
- JSON logs
- Prometheus metrics
- OpenTelemetry traces
```

## Request lifecycle

The intended gateway flow is:

1. A client application sends a request with an application API key.
2. The API authenticates the key using hashed storage and resolves the project/application context.
3. The API selects the active prompt version and model route for the request environment.
4. The provider adapter calls a mock or real LLM provider.
5. The API records request status, latency, token estimates, cost estimates, model/provider metadata, and error category.
6. Logs, metrics, and traces are emitted with request and trace identifiers.
7. The web dashboard reads summary and request data from API endpoints.

Phase 4 implements the first vertical slice of this flow with API key authentication, active prompt lookup, active model route lookup, a mock provider adapter, and persisted gateway request status.

Phase 5 adds latency measurement, token estimates, static mock-provider cost calculation, provider failure/timeout categorization, cost records, and a usage summary endpoint.

Phase 6 adds operator-facing API controls for prompt versions and model routes. Config changes write audit log records with actor metadata. Production-grade admin authorization is intentionally deferred to the later security hardening phase.

This flow intentionally avoids advanced RAG behavior. Retrieval, citations, document ingestion, and benchmark-driven answer quality stay in Proofbase.

## Application components

### API

Responsibilities:

- health and readiness endpoints
- API key authentication
- LLM gateway endpoint
- prompt version lookup
- model route selection
- provider adapter call
- request logging
- cost calculation
- latency tracking
- failure categorization
- metrics/logs/traces

### Web dashboard

Responsibilities:

- usage overview
- cost overview
- latency overview
- error overview
- request table
- prompt versions
- model routes

Phase 7 implements the first dashboard screen against real API endpoints.

### PostgreSQL

Stores:

- projects
- applications
- API keys
- prompt versions
- model routes
- gateway requests
- cost records
- audit logs

Phase 3 defines these tables through SQLAlchemy models and Alembic migrations. Later phases attach API behavior to the schema.

### Redis

Used for:

- rate limiting
- lightweight caching
- optional worker queue support

Redis is not required for Phase 1, but it is part of the target production architecture because rate limiting and short-lived operational state are realistic LLM gateway concerns.

## Infrastructure architecture

### AWS

Planned services:

- EKS
- ECR
- RDS PostgreSQL
- ElastiCache Redis
- Secrets Manager
- IAM
- VPC/subnets/security groups
- S3/DynamoDB for Terraform state locking if configured
- Optional Route 53/ACM

Terraform environments will stay explicit:

- `infra/terraform/environments/dev`
- `infra/terraform/environments/staging`
- `infra/terraform/environments/prod`

Reusable modules will live under `infra/terraform/modules` and should avoid hardcoded account IDs, secrets, or environment-specific assumptions.

Phase 11 adds the AWS foundation modules for network, ECR, IAM, and Secrets Manager placeholders. Phase 12 adds the EKS cluster module with managed node groups, cluster/node IAM roles, workload identity OIDC provider, and Kubernetes provider wiring.

Phase 13 adds private RDS PostgreSQL and ElastiCache Redis modules with security group ingress scoped to the EKS cluster security group, encryption, backups/snapshots, and staging/prod high-availability defaults.

### Kubernetes

Workloads:

- API Deployment
- Web Deployment
- optional Worker Deployment
- Services
- Ingress
- ExternalSecrets
- ConfigMaps
- ServiceAccounts
- HPA
- PodDisruptionBudget
- NetworkPolicies

Raw manifests are planned first so the Kubernetes shape is visible before it is abstracted into Helm. The Helm chart will then become the release artifact for dev, staging, and production.

Phase 14 adds raw Kustomize-compatible Kubernetes manifests for namespace, service accounts, ConfigMaps, API/web Deployments, Services, and Ingress. The manifests reference runtime secrets by name only and include probes, resource requests/limits, rolling update strategy, and non-root security contexts.

Phase 15 packages the same workload shape as a Helm chart with dev, staging, and prod values. Helm becomes the release abstraction used by later continuous deployment, promotion, and rollback phases.

Phase 19 adds OpenTelemetry tracing inside the API. The request middleware creates an `api.request` span, propagates `X-Request-ID`, and emits correlated request logs. The gateway service creates child spans for authentication, prompt lookup, model routing, provider execution, database writes, and response serialization. Tracing is disabled by default and can export to console or an OTLP HTTP collector when enabled.

Phase 20 adds Prometheus metrics through the API `/metrics` endpoint. Metrics cover HTTP volume and latency, gateway request/error counts, gateway latency, estimated LLM cost, token usage, API key auth failures, and rate-limit rejections. Labels stay bounded to method, route, status, provider, model, environment, gateway status, token type, and error category.

Phase 21 adds Grafana dashboard JSON and provisioning configuration for overview, reliability, and cost dashboards. Panels map to the Prometheus metrics emitted by the API; Grafana and Prometheus deployment remain later operational packaging work.

### Observability

- Prometheus for metrics
- Grafana for dashboards
- Loki for logs
- OpenTelemetry for traces
- Alertmanager or equivalent alert routing placeholder

Every gateway request should eventually be traceable across:

- API request handling
- authentication
- prompt lookup
- model route selection
- provider call
- database persistence
- response serialization

Logs should avoid secrets and sensitive prompt content by default.

## Environment strategy

### Local

- Docker Compose
- local PostgreSQL
- local Redis
- mock LLM provider
- no cloud dependency

Phase 2 implements the local skeleton with API and web health checks plus PostgreSQL and Redis containers. Database schema, migrations, gateway persistence, and Redis-backed behavior begin in later phases.

### Dev

- auto-deploy from main
- small infrastructure
- relaxed capacity
- separate namespace and secrets
- optimized for fast iteration and inexpensive operation

### Staging

- manual deploy
- production-like config
- pre-prod validation
- full observability
- release candidate validation before production

### Prod

- approval required
- conservative settings
- backups
- rollback
- alerts
- stricter security

## Repository map

```text
apps/
  api/                         FastAPI service, gateway routes, persistence, observability
  web/                         Next.js dashboard

infra/
  terraform/
    environments/              dev/staging/prod root modules
    modules/                   reusable AWS modules
  helm/
    ai-platform/               release chart and environment values
  k8s/
    base/                      raw base manifests before Helm
    overlays/                  dev/staging/prod overlays

.github/
  workflows/                   CI, deploy, and rollback automation

docs/                          architecture, deployment, operations, security, cost, demo plan
```

## Phase boundaries

Phase 1 defines documentation and repository shape only.

Later phases add:

- application skeleton and Docker Compose
- database models and migrations
- gateway API behavior
- dashboards
- Docker images
- CI/CD
- Terraform modules
- Kubernetes and Helm deployment
- observability, security, reliability, and cost controls

## Design principles

- Infrastructure is code.
- Environments are explicit.
- Secrets are never committed.
- App configuration is externalized.
- Releases are traceable.
- Rollbacks are documented.
- Metrics, logs, and traces are first-class.
- Cost is measured and explained.
