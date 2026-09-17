> Historical document. Current behavior and scope are described in the [documentation index](../README.md).

# Architecture

## Overview

This project is a production-style LLMOps platform.

Current implementation: Java 21/Spring Boot is the default API runtime after Phase
58; Python remains a contract reference. AWS deployment remains gated. Terraform
owns the ALB, TLS listener, host rules, security groups and IP target groups. A
restricted v3.5.0 controller reads Kubernetes endpoints and registers targets via
bootstrap-approved immutable TargetGroupBindings. It cannot write Ingress or
manage AWS load-balancer resources. See [the tested ownership design](../targetgroupbinding-design.md)
for admission, bootstrap order and remaining risks. Later sections describing the
original Python phases are historical implementation notes.

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
 Terraform-owned ALB
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

The implemented gateway flow includes API key authentication, active prompt lookup, active model route lookup, a mock provider adapter, persisted gateway request status, latency measurement, token estimates, static mock-provider cost calculation, provider failure/timeout categorization, cost records, and usage endpoints.

Operator-facing API controls manage prompt versions and model routes. Config changes write audit log records with actor metadata. Production-grade admin authorization is intentionally out of scope for this baseline.

This flow intentionally avoids advanced RAG behavior. Retrieval, citations, document ingestion, and benchmark-driven answer quality stay in Proofbase.

For a developer-focused walkthrough of the gateway code path, see [gateway-flow.md](../gateway-flow.md).

## External telemetry integration

Proofbase is connected through normalized telemetry before any provider calls are routed through the gateway. The event schema and privacy rules are defined in [external-telemetry-contract.md](../external-telemetry-contract.md), and the completed integration summary lives in [proofbase-integration.md](../proofbase-integration.md).

In that model:

1. Proofbase continues to call its own AI provider paths for RAG chat, streaming chat, Markdown cleanup, query decomposition, and embeddings.
2. Proofbase sends a bounded LLM usage event to Production AI Platform after each safe AI operation.
3. Production AI Platform authenticates the client application, validates the event, persists usage and cost data, emits metrics, and shows the traffic in the dashboard.
4. If Production AI Platform is unavailable, Proofbase continues serving users and records the telemetry failure locally.

This preserves the project boundary: Proofbase owns the AI product layer, while this repository owns centralized operations visibility.

AgentOps Workflow Platform is connected through the same normalized telemetry path. The completed integration summary lives in [agentops-integration.md](../agentops-integration.md).

In that model:

1. AgentOps continues to execute its own workflows, agent steps, structured generation, retries, tool behavior, and local cost tracking.
2. AgentOps sends bounded LLM usage events for safe agent-step and workflow-summary operations.
3. Production AI Platform authenticates the AgentOps application key, validates the event, persists usage and cost data where appropriate, emits metrics, and shows the traffic in the dashboard.
4. If Production AI Platform is unavailable, AgentOps continues running workflows and records a redacted local diagnostic entry.

This preserves the second project boundary: AgentOps owns the agent workflow layer, while this repository owns centralized operations visibility.

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

The dashboard reads real API endpoints for usage, costs, latency, failures, prompt versions, and model routes.

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

These tables are defined through SQLAlchemy models and Alembic migrations, and the gateway, admin, usage, audit, and dashboard flows use them.

### Redis

Used for:

- rate limiting
- lightweight caching
- optional worker queue support

Redis is part of the target production architecture because distributed rate limiting and short-lived operational state are realistic LLM gateway concerns. The current baseline uses in-process rate limiting locally.

## Infrastructure architecture

### AWS

AWS services represented in Terraform:

- EKS
- ECR
- RDS PostgreSQL
- ElastiCache Redis
- Secrets Manager
- IAM
- VPC/subnets/security groups
- S3/DynamoDB for Terraform state locking if configured
- Optional Route 53/ACM

Terraform environments are explicit:

- `infra/terraform/environments/dev`
- `infra/terraform/environments/staging`
- `infra/terraform/environments/prod`

Reusable modules live under `infra/terraform/modules` and avoid hardcoded account IDs, secrets, or environment-specific assumptions.

Terraform includes AWS foundation modules for network, ECR, IAM, Secrets Manager placeholders, EKS, RDS PostgreSQL, ElastiCache Redis, and optional budgets. Data services use private networking, encryption, backup/snapshot defaults, EKS-scoped security group ingress, and staging/prod high-availability settings. Restore paths, Terraform state recovery, Redis persistence tradeoffs, and single-region DR assumptions are documented.

### Kubernetes

Workloads:

- API Deployment
- Web Deployment
- optional Worker Deployment
- Services
- Terraform-owned ALB and bootstrap-owned TargetGroupBindings
- ExternalSecrets
- ConfigMaps
- ServiceAccounts
- HPA
- PodDisruptionBudget
- NetworkPolicies

Raw manifests keep the Kubernetes shape visible, while the Helm chart is the primary release artifact for dev, staging, and production.

The repository includes raw Kustomize-compatible Kubernetes manifests for namespace, service accounts, ConfigMaps, API/web Deployments, Services, Ingress, External Secrets, HPAs, PDBs, and NetworkPolicies. The Helm chart packages the same workload shape with dev, staging, and prod values for continuous deployment, promotion, and rollback workflows.

Phase 19 adds OpenTelemetry tracing inside the API. The request middleware creates an `api.request` span, propagates `X-Request-ID`, and emits correlated request logs. The gateway service creates child spans for authentication, prompt lookup, model routing, provider execution, database writes, and response serialization. Tracing is disabled by default and can export to console or an OTLP HTTP collector when enabled.

Phase 20 adds Prometheus metrics through the API `/metrics` endpoint. Metrics cover HTTP volume and latency, gateway request/error counts, gateway latency, estimated LLM cost, token usage, API key auth failures, and rate-limit rejections. Labels stay bounded to method, route, status, provider, model, environment, gateway status, token type, and error category.

Grafana dashboard JSON and provisioning configuration cover overview, reliability, cost, and logs dashboards. Panels map to the Prometheus metrics and structured logs emitted by the API; live Grafana and Prometheus installation remains environment-specific.

Phase 22 adds Loki/Promtail integration assets for structured JSON logs. Logs remain searchable by request ID and trace ID through JSON parsing instead of high-cardinality Loki labels, and a Grafana logs dashboard provides error-rate, 5xx, latency, and recent-error panels.

Phase 23 adds Prometheus alert rules and an Alertmanager placeholder for high gateway errors, high p95 latency, elevated 5xx responses, pod restarts, PostgreSQL connectivity failure, and estimated LLM cost spikes. Runbook and incident response docs map these alerts to triage and rollback decisions.

Phase 24 adds External Secrets integration. AWS Secrets Manager stores runtime values outside Terraform state, External Secrets Operator syncs them into `ai-platform-runtime-secrets`, and the API Deployment continues to consume that Kubernetes Secret without plaintext manifests.

Phase 25 adds security hardening. The gateway applies a bounded in-memory fixed-window rate limit keyed by API key hash. Raw Kubernetes manifests and the Helm chart render default-deny ingress NetworkPolicies plus explicit API and web ingress allowances. Workloads continue to use dedicated service accounts with token automounting disabled, non-root pod security contexts, dropped Linux capabilities, no privilege escalation, and read-only root filesystems. CI now treats Python dependency audit findings as blocking and adds a repository-level Trivy filesystem scan for high/critical vulnerability, config, and secret findings.

Phase 26 adds autoscaling and resilience controls. Raw manifests and Helm render API/web HPAs and PodDisruptionBudgets, workloads drain with termination grace periods and preStop delays, the API readiness endpoint fails during shutdown, provider calls use bounded retry settings, and `scripts/smoke_load.py` provides a small repeatable gateway load smoke test.

### Observability

- Prometheus for metrics
- Grafana for dashboards
- Loki for logs
- OpenTelemetry for traces
-- Alertmanager or equivalent alert routing configuration

Every gateway request is designed to be traceable across:

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

Local development uses Docker Compose with API and web health checks plus PostgreSQL and Redis containers. Database schema, migrations, gateway persistence, and dashboard reads are available locally after migrations and seed data.

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

## Scope Boundary

The repository intentionally focuses on the platform and operations layer: gateway, dashboard, CI/CD, Terraform, Kubernetes, Helm, observability, security, reliability, and cost controls. Advanced RAG features such as document ingestion, vector retrieval, citations, permission-aware retrieval, and benchmark-driven answer quality belong in Proofbase rather than this repository. Agent workflow execution, prompts, generated outputs, tool payloads, and workflow state belong in AgentOps rather than this repository.

## Design principles

- Infrastructure is code.
- Environments are explicit.
- Secrets are never committed.
- App configuration is externalized.
- Releases are traceable.
- Rollbacks are documented.
- Metrics, logs, and traces are first-class.
- Cost is measured and explained.
