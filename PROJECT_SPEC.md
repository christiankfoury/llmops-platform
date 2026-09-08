# PROJECT_SPEC.md

# Production AI Platform / LLMOps Infrastructure Platform

## One-line description

A production-style LLMOps portfolio project with an LLM gateway and usage dashboard, demonstrating Terraform, Kubernetes, Helm, CI/CD, observability, secrets, rollback, backup/restore and cost controls in one approved AWS dev/demo environment.

## Why this project exists

Active implementation direction (2026-09-06): convert the existing FastAPI backend to Java 21/Spring Boot while retaining AWS, PostgreSQL, the Next.js dashboard, and both telemetry client contracts. The Python runtime remains the reference until compatibility, authorization, and container cutover are validated. Phases 48-69 add the Java conversion, remaining access controls/reliability, AWS release validation, running monitoring, recovery evidence, and gated public release. See [the Java/AWS implementation plan](docs/java-aws-implementation-plan.md). Completed historical phases do not imply live AWS deployment or completion of this new sequence.

Continuation status (2026-09-08): Java conversion/cutover and release preparation
through Phase 61 are completed. Phase 62 monitoring remains incomplete with
vulnerability remediation deferred. The owner-selected continuation is independent
Phases 63-65 preparation under the scoped AGENTS.md override, then the Phase 66
AWS setup/approval gate. This does not remove runnable monitoring from the product
or grant deployment eligibility. See [the handoff](docs/next-chat-handoff.md).

Completion scope (owner direction, 2026-09-08): bounded local verification,
focused security/demo preparation and one approved AWS dev/demo deployment.
Separate staging and production deployments are optional future work; their
existing configuration remains available for static review. No production SLA,
customer workload or multi-environment AWS operating claim is implied. See the
[portfolio completion plan](docs/portfolio-completion-plan.md).

This project is designed as a portfolio piece for DevOps/cloud, backend, full-stack, and AI engineering roles.

The application is intentionally simple but realistic. The infrastructure around it is the main showcase.

The project should prove:

- I can build a real backend and dashboard.
- I can deploy production-style workloads to Kubernetes.
- I can manage cloud infrastructure with Terraform.
- I understand CI/CD, staged environments, rollback, and release safety.
- I can add observability with metrics, logs, and traces.
- I can handle secrets and security controls responsibly.
- I can reason about reliability and cost.

## Portfolio relationship

This project is intentionally complementary to Proofbase.

Proofbase is the AI product portfolio piece: permission-aware enterprise RAG, document workflows, retrieval quality, citations, memory safety, and benchmark-driven answer evaluation.

Production AI Platform is the AI operations portfolio piece: a shared LLM gateway with API keys, prompt versions, model routing, request logging, cost/latency/error tracking, deployment automation, cloud infrastructure, observability, secrets, rollback, and reliability runbooks.

The clean portfolio story is:

1. Proofbase shows I can build a serious enterprise AI application.
2. Production AI Platform shows I can productionize and operate AI workloads.

Future integration path: Proofbase should connect to this platform in two steps. First, Proofbase sends normalized LLM usage telemetry into Production AI Platform while continuing to own RAG, retrieval, citations, permission filtering, memory behavior, and answer-quality evaluation. This gives centralized cost, latency, token, error, request, and dashboard visibility without risking Proofbase's product correctness. Later, after the gateway supports the richer provider contract Proofbase needs, selected Proofbase provider calls can be routed through the gateway for centralized model routing and operational controls.

## Target audience

Recruiters and hiring managers for:

- DevOps Engineer
- Cloud Engineer
- Platform Engineer
- Infrastructure Engineer
- Backend Engineer
- AI Engineer
- LLMOps Engineer
- Full-stack Engineer with cloud strength

## Final portfolio claim

> Built and demonstrated a production-style LLMOps platform in one AWS dev/demo environment using Java, Kubernetes, Terraform, Helm, GitHub Actions, Prometheus, Grafana, Loki, OpenTelemetry, managed PostgreSQL, Redis, external secrets, request tracing, cost monitoring, and tested release/rollback and local backup/restore procedures.

Use this target claim only after the approved AWS demonstration and its evidence exist. Staging/production configurations are optional, statically validated designs unless separately deployed and tested.

## Product concept

The platform lets internal applications send requests to an LLM gateway instead of calling model providers directly.

The gateway centralizes:

- API key authentication
- Prompt versioning
- Model routing
- Request logging
- Cost tracking
- Latency tracking
- Error tracking
- Usage analytics
- Operational monitoring

## Core user stories

### Platform operator

As a platform operator, I want to demonstrate a controlled release, monitoring and rollback in one AWS dev/demo environment, with reusable staging/prod configurations available as optional future work.

### Application developer

As an application developer, I want an API key for my app so that I can send LLM requests through the gateway and track usage.

As an application developer with an existing AI app, I want to submit normalized LLM usage telemetry to the platform so that my app's model usage, cost, latency, and failures can be monitored centrally before I migrate provider calls through the gateway.

### Engineering manager

As an engineering manager, I want dashboards for cost, latency, and errors so that I can understand AI platform health and usage.

### DevOps engineer

As a DevOps engineer, I want infrastructure, release, rollback, secrets, and monitoring to be codified so that the platform can be operated safely.

### Security reviewer

As a security reviewer, I want secrets, IAM, network access, and audit logs handled responsibly so that the platform does not expose sensitive data or overprivileged access.

## Core application features

### LLM gateway

The gateway should accept requests from client apps and route them to a selected model provider.

Initial implementation can use a mock provider. Real provider integration can be added later if needed.

Gateway should record:

- request ID
- project ID
- application ID
- API key ID
- prompt version ID
- model selected
- provider selected
- request status
- latency
- estimated input tokens
- estimated output tokens
- estimated cost
- error category
- created timestamp

### API keys

Each application should have an API key.

API keys should support:

- hashed storage
- active/inactive status
- last-used timestamp
- project/application ownership
- audit logging for key creation/revocation

### Prompt versioning

Prompt versions should support:

- name
- version number
- content/template
- active/inactive status
- project/application scope
- created timestamp
- updated timestamp

### Model routing

Model routes should support:

- project/application/environment scope
- provider name
- model name
- priority or default flag
- active/inactive status

### Cost tracking

Cost estimates should be calculated from token usage and model pricing config.

The first version can use static pricing stored in code or database seed data.

### Dashboard

The dashboard should show:

- total requests
- estimated cost
- error rate
- average latency
- p95 latency where available
- recent requests
- recent failures
- cost by model
- requests by model
- prompt versions
- model routes

### External telemetry ingestion

Existing AI applications should be able to connect to the platform before fully routing calls through the gateway.

The first integration target is Proofbase (`enterprise-knowledge-agent`). Proofbase should remain the AI product layer and should not move RAG-specific behavior into this repository. The platform should receive safe, normalized telemetry events for Proofbase AI operations such as RAG chat generation, streaming chat generation, AI Markdown cleanup, query decomposition, and embedding generation where cost/token data can be represented honestly.

The second integration target is AgentOps Workflow Platform (`agentops-workflow-platform`). AgentOps should remain the agent workflow/orchestration layer and should not move workflow execution, agent prompts, structured outputs, tool payloads, or workflow state into this repository. The platform should receive safe, normalized telemetry events for AgentOps workflow and agent-step operations where model, token, latency, status, retry, and estimated-cost data can be represented honestly.

External telemetry events should support:

- source application identity
- operation type
- external request ID
- project/application attribution
- model and provider
- prompt name and version when available
- input and output tokens when available
- estimated cost when available
- latency
- status
- error category
- bounded metadata

External telemetry events should not include by default:

- API keys
- provider credentials
- full prompts
- full user questions
- retrieved chunks
- citations
- uploaded document text
- extracted Markdown
- raw customer or employee data

Telemetry submission should be best-effort for client apps. If the platform is unavailable, the client app should keep serving users and record the telemetry failure locally without exposing secrets.

The detailed Phase 31 contract is documented in `docs/external-telemetry-contract.md`. It defines the external telemetry taxonomy, required and optional fields, sensitive-data exclusions, idempotency strategy, retry behavior, and client-app boundaries. The Proofbase summary is documented in `docs/proofbase-integration.md`; the AgentOps summary is documented in `docs/agentops-integration.md`; and the AgentOps phase notes live in `docs/agentops-integration-plan.md`.

## Infrastructure goals

Current release scope: local development plus one approved AWS dev/demo
environment. Staging and production goals below describe optional designs, not
required live deployments. Existing configuration still receives applicable
static validation; do not represent those environments as tested in AWS.

### Local

Local environment should run with:

- Docker Compose
- API
- web dashboard
- PostgreSQL
- Redis
- optional local mock services

### Dev

Dev environment should:

- deploy a verified main revision through approved release workflows
- use smaller infrastructure
- allow fast iteration
- use separate secrets and namespace

### Staging (optional future deployment)

If separately selected and approved, staging should:

- mirror production closely
- deploy manually
- be used for release validation
- have realistic observability

### Prod (optional future deployment)

If separately selected and approved, production should:

- require approval
- use conservative scaling defaults
- use stricter security
- have backups enabled
- have rollback path documented

## Cloud target

Default cloud: AWS.

Primary AWS services:

- EKS for Kubernetes
- ECR for container registry
- RDS PostgreSQL for database
- ElastiCache Redis for cache/queue
- Secrets Manager for secrets
- IAM/OIDC for workload identity
- CloudWatch optional as supporting service
- Route 53 and ACM optional if domain/TLS is implemented directly through AWS
- S3 optional for Terraform state and artifacts

## Kubernetes requirements

The platform should eventually include:

- namespaces per environment
- deployments
- services
- Terraform-owned ALB routing and bootstrap-approved immutable TargetGroupBindings; the controller has no Ingress writes
- ConfigMaps
- ExternalSecrets
- service accounts
- readiness probes
- liveness probes
- resource requests
- resource limits
- HPA
- PodDisruptionBudget
- NetworkPolicies
- rolling updates
- rollback support

## CI/CD requirements

CI should include:

- backend lint
- backend tests
- frontend lint
- frontend typecheck
- frontend tests where practical
- Docker builds
- dependency scanning
- image scanning
- Terraform format/validate
- Helm lint/template

CD should include:

- automatic dev deploy
- manual staging deploy
- production approval
- immutable image tags
- post-deploy smoke test
- rollback workflow

## Observability requirements

### Logs

Use structured JSON logs.

Logs should include:

- request ID
- trace ID
- project/application ID where safe
- route
- status
- latency
- error category

Never log:

- API key values
- raw secrets
- full sensitive prompts by default
- provider credentials

### Metrics

Expose metrics for:

- request count
- error count
- latency histogram
- token usage
- estimated cost
- model route count
- rate limit rejections
- auth failures

### Tracing

Trace:

- request start
- authentication
- prompt lookup
- model routing
- provider call
- database write
- response

## Security requirements

Security should include:

- no committed secrets
- hashed API keys
- least-privilege IAM
- External Secrets integration
- NetworkPolicies
- non-root containers where possible
- image scanning
- dependency scanning
- rate limiting
- audit logs
- environment isolation

## Reliability requirements

Reliability should include:

- health checks
- readiness checks
- graceful shutdown
- retries with limits
- provider timeouts
- rolling updates
- rollback workflow
- database backups
- restore docs
- incident response runbook
- alert rules

## Cost requirements

Cost controls should include:

- estimated LLM cost per request
- dashboard cost summary
- cost by model
- cloud cost estimate
- environment sizing notes
- dev teardown guidance
- optional AWS budget alert

## Non-goals

This project should not become a huge AI product.

Avoid over-focusing on:

- complex agent workflows
- advanced RAG, vector retrieval, citation validation, document ingestion, and benchmark-driven answer evaluation
- fine-tuning
- multi-modal AI
- elaborate chat UX
- enterprise billing
- multi-tenant compliance complexity beyond portfolio scope

## Success criteria

The project is successful when:

- It runs locally.
- It has a working LLM gateway and dashboard.
- Infrastructure is defined in Terraform.
- The app can be deployed to Kubernetes with Helm.
- CI/CD is implemented.
- Observability is visible.
- Secrets are handled safely.
- Rollback and incident response are documented.
- The README clearly sells the DevOps/cloud value.
