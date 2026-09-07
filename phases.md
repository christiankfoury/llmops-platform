# phases.md

# Production AI Platform / LLMOps Infrastructure Platform Roadmap

This roadmap is designed for Codex to implement phases sequentially as an autonomous phase-based engineering agent. Each phase should be small enough for a focused commit and review, while the full project becomes a strong DevOps/cloud portfolio piece.

Codex should complete the current `In Progress` phase, commit it, push it to `main`, review the pushed commit, fix each top finding in a separate follow-up commit, push each fix to `main`, write the phase review, then move automatically to the next phase unless a stop condition in `AGENTS.md` requires human approval or a blocker prevents safe progress.

The app should stay intentionally scoped. The infrastructure, delivery workflow, observability, security, and reliability story are the main differentiators.

## Phase 1: Project specification and architecture

Define the complete product and infrastructure scope before writing application code.

Deliverables:

- `PROJECT_SPEC.md`
- `README.md` initial version
- `docs/architecture.md`
- Initial repository structure
- Environment strategy: local, dev, staging, prod
- Cloud target decision: AWS
- Final portfolio claims
- Non-goals and scope boundaries

Acceptance criteria:

- The product goal is clear.
- The target architecture is documented.
- The infrastructure story is visible from the README.
- The project can be understood by a recruiter or engineer without asking for extra context.

## Phase 2: Minimal monorepo and local development foundation

Create the initial app skeleton and local development workflow.

Deliverables:

- `apps/api` FastAPI skeleton
- `apps/web` Next.js skeleton
- Shared environment examples
- Local Docker Compose with API, web, PostgreSQL, and Redis
- Basic health endpoints
- Basic landing dashboard page
- Initial Makefile or task runner commands

Acceptance criteria:

- Developer can run the platform locally with one command.
- API health endpoint works.
- Web app loads and can call API health endpoint.
- PostgreSQL and Redis start locally.
- No real secrets are committed.

## Phase 3: Database schema and migrations

Add the database model foundation for the LLMOps platform.

Deliverables:

- SQLAlchemy models or equivalent
- Alembic migration setup
- Tables for:
  - organizations or projects
  - applications
  - API keys
  - prompt versions
  - model routes
  - gateway requests
  - cost records
  - audit logs
- Seed/dev data script

Acceptance criteria:

- Migrations run locally.
- Seed data creates at least one project, app, API key placeholder, prompt version, and model route.
- Schema supports later usage, cost, latency, and error dashboards.

## Phase 4: LLM gateway API foundation

Implement the core gateway request path.

Deliverables:

- Gateway endpoint, such as `POST /v1/gateway/completions`
- API key authentication
- Project/application resolution
- Prompt version lookup
- Model route selection
- Mock provider adapter for local/test use
- Request/response persistence

Acceptance criteria:

- A request with a valid API key reaches the mock provider.
- A request with an invalid API key is rejected.
- Gateway request is recorded with project, app, prompt version, model, status, and timestamps.
- Tests cover success and auth failure paths.

## Phase 5: Cost, latency, and failure tracking

Make the gateway useful as an LLMOps system.

Deliverables:

- Token usage fields
- Estimated cost calculation
- Latency measurement
- Error category tracking
- Provider timeout handling
- Provider failure handling
- Request status model
- Basic usage summary endpoint

Acceptance criteria:

- Every gateway request records latency.
- Successful requests record estimated token and cost data.
- Failed requests record error type and failure status.
- Usage summary endpoint returns request count, error count, average latency, and estimated cost.

## Phase 6: Prompt versioning and model routing controls

Add operator-facing configuration for prompt and model behavior.

Deliverables:

- CRUD endpoints for prompt versions
- CRUD endpoints for model routes
- Active/inactive prompt version behavior
- Route selection rules by project/app/environment
- Basic audit logging for config changes

Acceptance criteria:

- Admin can create and activate a prompt version.
- Admin can update model routing rules.
- Gateway uses active prompt and route configuration.
- Config changes are audit logged.

## Phase 7: Dashboard MVP

Create the first usable web dashboard.

Deliverables:

- Dashboard layout
- Usage summary cards
- Request table
- Error table
- Latency view
- Cost view
- Prompt version view
- Model route view

Acceptance criteria:

- Dashboard shows real data from API.
- User can see requests, latency, errors, and estimated cost.
- UI is simple but recruiter-demo friendly.

## Phase 8: API and frontend quality baseline

Add enough test coverage and quality checks to support serious CI.

Deliverables:

- Backend linting
- Backend formatting
- Backend tests
- Frontend linting
- Frontend typecheck
- Frontend tests where practical
- Pre-commit or equivalent optional
- Test documentation

Acceptance criteria:

- Local checks can be run with one documented command.
- CI-ready commands exist.
- Basic gateway and dashboard functionality is covered.

## Phase 9: Docker production images

Build production-ready Docker images.

Deliverables:

- API Dockerfile
- Web Dockerfile
- `.dockerignore` files
- Multi-stage builds where useful
- Non-root runtime user where practical
- Container health checks
- Local image build documentation

Acceptance criteria:

- API image builds.
- Web image builds.
- Images do not include unnecessary files.
- Runtime configuration comes from environment variables.

## Phase 10: CI pipeline

Add the main GitHub Actions CI workflow.

Deliverables:

- `.github/workflows/ci.yml`
- Backend lint/test job
- Frontend lint/typecheck/test job
- Docker build job
- Dependency scan
- Image scan
- Terraform formatting check placeholder
- Helm lint placeholder

Acceptance criteria:

- CI runs on pushes to main.
- Pull request checks may be supported as optional repository hygiene, but the autonomous Codex flow targets main.
- CI blocks obvious failures.
- Security scanning is included.
- Workflow is documented.

## Phase 11: Terraform AWS foundation

Create Terraform foundation for AWS infrastructure.

Deliverables:

- Terraform environment folders for dev, staging, prod
- Modules for:
  - network/VPC
  - ECR registry
  - IAM basics
  - secrets placeholders
- Remote state documentation
- Environment variable documentation

Acceptance criteria:

- Terraform is formatted and validates structurally.
- Environments are clearly separated.
- No real credentials or account-specific secrets are committed.
- Tags and naming conventions are defined.

## Phase 12: Terraform EKS cluster

Provision Kubernetes cluster infrastructure.

Deliverables:

- EKS module
- Node group or managed node configuration
- Cluster IAM roles
- OIDC provider for workload identity
- Kubernetes provider wiring
- Cluster access docs

Acceptance criteria:

- EKS module is reusable.
- Dev/staging/prod can configure cluster size separately.
- Workload identity path is documented.
- Terraform validates.

## Phase 13: Terraform managed data services

Add managed PostgreSQL and Redis infrastructure.

Deliverables:

- RDS PostgreSQL module
- ElastiCache Redis module or documented dev alternative
- Security groups
- Subnet placement
- Backup settings
- Parameter defaults
- Secret references for credentials

Acceptance criteria:

- Database and Redis are private by default.
- Backups are enabled for non-dev environments.
- Credentials are not hardcoded.
- Connection information can be consumed by Kubernetes later.

## Phase 14: Base Kubernetes manifests

Create raw Kubernetes manifests before Helm abstraction.

Deliverables:

- Namespace
- API Deployment and Service
- Web Deployment and Service
- Worker placeholder if needed
- ConfigMaps
- Secret references
- Ingress
- Readiness probes
- Liveness probes
- Resource requests and limits

Acceptance criteria:

- Manifests render/apply structurally.
- API and web have probes and resource limits.
- Secrets are referenced, not hardcoded.
- Environment-specific values are not duplicated excessively.

## Phase 15: Helm chart

Convert Kubernetes deployment into a reusable Helm chart.

Deliverables:

- `infra/helm/ai-platform/Chart.yaml`
- `values.yaml`
- `values-dev.yaml`
- `values-staging.yaml`
- `values-prod.yaml`
- Templates for API, web, ingress, config, secrets references, service accounts, HPA
- Helm lint/template documentation

Acceptance criteria:

- `helm lint` passes.
- `helm template` works for dev, staging, and prod.
- Image tags and environment settings are configurable.
- Chart supports safe staged deployments.

## Phase 16: Continuous deployment to dev

Deploy dev automatically from the main branch.

Deliverables:

- `deploy-dev.yml`
- Build and push images to ECR
- Helm upgrade/install to dev namespace
- Kubernetes context setup docs
- Deployment status check
- Smoke test after deploy

Acceptance criteria:

- Dev deployment is automated.
- Image tags are traceable to commit SHA.
- Failed smoke test fails the workflow.
- Deployment does not require committed secrets.

## Phase 17: Staging and production release workflows

Add controlled promotion workflows.

Deliverables:

- `deploy-staging.yml`
- `deploy-prod.yml`
- Manual approval gate for prod
- Release notes generation or template
- Environment-specific Helm values
- Promotion documentation

Acceptance criteria:

- Staging deploy can be triggered manually.
- Production deploy requires explicit approval.
- Prod settings are more conservative than dev.
- Release process is documented.

## Phase 18: Rollback workflow

Add operational rollback support.

Deliverables:

- `rollback.yml`
- Helm rollback command workflow
- Rollback documentation
- Failed deployment recovery steps
- Verification steps after rollback

Acceptance criteria:

- A previous release can be selected.
- Workflow documents rollback risks.
- Runbook explains when to rollback versus hotfix.
- Dashboard/readiness verification is included.

## Phase 19: OpenTelemetry tracing

Instrument the app for distributed tracing.

Deliverables:

- OpenTelemetry setup in API
- Request ID propagation
- Trace ID in logs
- Spans for:
  - gateway request
  - auth
  - prompt lookup
  - model routing
  - provider call
  - database write
- Collector deployment or integration docs

Acceptance criteria:

- Traces include gateway request lifecycle.
- Logs include trace/request IDs.
- Tracing can be enabled or disabled by environment config.
- Tests or local docs verify instrumentation path.

## Phase 20: Prometheus metrics

Expose production-useful metrics.

Deliverables:

- `/metrics` endpoint
- Request count metric
- Error count metric
- Latency histogram
- Estimated cost metric
- Token usage metric
- Rate limit rejection metric
- Kubernetes ServiceMonitor or scrape annotation

Acceptance criteria:

- Prometheus can scrape API metrics.
- Metrics use clear labels without high cardinality mistakes.
- Dashboard-critical metrics exist.
- Documentation explains each metric.

## Phase 21: Grafana dashboards

Create recruiter-visible and operator-useful dashboards.

Deliverables:

- Grafana dashboard JSON/provisioning
- Overview dashboard:
  - request volume
  - error rate
  - p95 latency
  - estimated cost
  - token usage
  - model distribution
- Reliability dashboard
- Cost dashboard
- Dashboard screenshots placeholder docs

Acceptance criteria:

- Dashboards can be provisioned.
- Panels map to real metrics.
- README can show screenshots after deployment.
- Dashboards support the final portfolio story.

## Phase 22: Loki structured logging

Add centralized logging.

Deliverables:

- Structured JSON logs
- Request ID and trace ID in logs
- Loki deployment or integration
- Promtail or logging agent config
- Log query examples
- Error log dashboard panel

Acceptance criteria:

- Logs are searchable by request ID.
- Logs correlate with traces.
- Sensitive values are not logged.
- Log examples are documented.

## Phase 23: Alerts and incident response

Add alerting and incident workflow docs.

Deliverables:

- Prometheus alert rules
- Alertmanager config placeholder
- Alerts for:
  - high error rate
  - high p95 latency
  - elevated 5xx
  - pod restarts
  - database connectivity failures
  - cost spike
- `docs/incident-response.md`
- `docs/runbook.md`

Acceptance criteria:

- Alerts are tied to real metrics.
- Runbook explains triage steps.
- Incident response doc includes severity levels.
- Demo incident scenario is documented.

## Phase 24: Secrets management

Move sensitive configuration into proper secret management.

Deliverables:

- External Secrets Operator manifests or Helm integration
- AWS Secrets Manager integration docs
- Service account/workload identity configuration
- Secret naming convention
- Local development fallback
- Rotation guidance

Acceptance criteria:

- Kubernetes apps reference External Secrets, not plaintext secrets.
- Secret access is scoped by environment.
- Docs explain how to create required secrets.
- No real secret values are committed.

## Phase 25: Security hardening

Add production security controls.

Deliverables:

- Kubernetes NetworkPolicies
- Pod security context
- Container security context
- Service accounts with least privilege
- API rate limiting
- Dependency scanning improvements
- Image scanning enforcement
- Basic audit log review endpoint or docs
- Security baseline documentation

Acceptance criteria:

- Workloads do not run as privileged.
- Network access is restricted where practical.
- API has rate limiting.
- Security posture is documented.
- CI catches common supply-chain issues.

## Phase 26: Autoscaling and resilience

Improve runtime reliability.

Deliverables:

- HorizontalPodAutoscaler
- PodDisruptionBudget
- Graceful shutdown handling
- Worker retry strategy if worker exists
- Provider timeout/retry policy
- Resource tuning notes
- Load test script or documented smoke load test

Acceptance criteria:

- API can scale based on CPU or custom metrics where practical.
- Rolling updates avoid obvious downtime.
- Provider failures are handled gracefully.
- Resilience behavior is documented.

## Phase 27: Backup and restore

Document and test recovery paths.

Deliverables:

- Database backup strategy
- Restore runbook
- Terraform state recovery notes
- Redis persistence/ephemeral decision
- Disaster recovery assumptions
- Recovery time/recovery point goals

Acceptance criteria:

- Non-dev database backup strategy is explicit.
- Restore steps are documented.
- DR assumptions are honest and portfolio-ready.
- Operational tradeoffs are explained.

## Phase 28: Cost controls and analysis

Make cost awareness part of the project story.

Deliverables:

- `docs/cost-analysis.md`
- Cloud cost estimate by environment
- Scaling cost assumptions
- LLM usage cost tracking explanation
- Budget alert Terraform placeholder or implementation
- Resource right-sizing notes
- Dev environment teardown guidance

Acceptance criteria:

- README can claim cost monitoring and cost controls honestly.
- Infra costs are estimated.
- LLM costs are visible in app/dashboard.
- Dev resources have clear cleanup instructions.

## Phase 29: GitOps with Argo CD

Add optional GitOps deployment capability.

Deliverables:

- Argo CD install docs or manifests
- Application manifests for dev/staging/prod
- Helm-based Argo CD app configuration
- Sync policy explanation
- Manual versus automated sync strategy

Acceptance criteria:

- GitOps flow is documented.
- Argo CD app points to Helm chart.
- Environment promotion story remains clear.
- This does not replace existing GitHub Actions release docs unless intentionally documented.

## Phase 30: Final documentation and portfolio polish

Package the project for recruiters and hiring managers.

Deliverables:

- Final README
- Architecture diagram
- Deployment diagram
- Dashboard screenshots
- Demo script
- Incident simulation write-up
- Cost report
- Security summary
- Reliability summary
- Final portfolio bullet points
- Known limitations

Acceptance criteria:

- A recruiter understands the project in 60 seconds.
- An engineer can inspect the repo and see real implementation depth.
- README clearly explains what was built, how it is deployed, how it is monitored, and how it fails safely.
- Final claims are accurate and backed by code/docs.

## Phase 31: Proofbase integration contract and event schema

Define the telemetry-first integration between Proofbase (`enterprise-knowledge-agent`) and this Production AI Platform before changing runtime behavior.

This phase intentionally avoids routing Proofbase LLM calls through the gateway. Proofbase should continue to own RAG, retrieval, citations, permissions, and answer-quality behavior. The Production AI Platform should receive normalized LLMOps telemetry so it can centralize cost, latency, token, error, and request visibility.

Deliverables:

- Shared external LLM event schema for client applications.
- Operation taxonomy for Proofbase events:
  - `rag_query`
  - `rag_query_stream`
  - `markdown_cleanup`
  - `query_decomposition`
  - `embedding_generation`
- Required versus optional event fields.
- Sensitive-data rules for telemetry payloads.
- Idempotency and external request ID strategy.
- Error and retry semantics for telemetry submission.
- Phase-level implementation notes for Proofbase first, AgentOps second.

Relevant files:

- `docs/gateway-flow.md`
- `docs/architecture.md`
- `docs/observability.md`
- `docs/security-baseline.md`
- `docs/portfolio-demo-plan.md`
- `PROJECT_SPEC.md`
- `README.md`
- Proofbase reference files:
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\main.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\generation\answer_generator.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\logger.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\costing\estimator.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\embeddings\openai_embeddings.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\projects\markdown_cleanup.py`

Acceptance criteria:

- The integration path is documented as telemetry-first.
- The event schema supports model, operation type, prompt version, input/output tokens, estimated cost, latency, status, error category, request ID, external request ID, project/application attribution, and metadata.
- The schema explicitly excludes API keys, provider credentials, full prompts, full questions, retrieved chunks, citations, document text, and raw customer data by default.
- The plan distinguishes Proofbase product-layer telemetry from Production AI Platform operations-layer responsibilities.

## Phase 32: External telemetry ingestion API

Add a central ingestion API for external client applications to send LLM usage events into Production AI Platform.

Deliverables:

- `POST /v1/usage/llm-events` or equivalent ingestion endpoint.
- Pydantic request/response schemas for external LLM events.
- Service layer that validates API key ownership and resolves project/application scope.
- Persistence into existing `gateway_requests` and `cost_records`, or a purpose-built external event model if existing gateway tables cannot represent the data cleanly.
- Error handling for invalid payloads, unknown applications, bad API keys, and duplicate external event IDs.
- Metrics emission for accepted events, rejected events, token totals, cost totals, and ingestion errors.
- Tests for success, validation failure, auth failure, duplicate handling, and cost aggregation.

Relevant files:

- `apps/api/app/api/usage.py`
- `apps/api/app/schemas/usage.py`
- `apps/api/app/services/usage.py`
- `apps/api/app/services/auth.py`
- `apps/api/app/models/gateway_request.py`
- `apps/api/app/models/cost_record.py`
- `apps/api/app/models/identity.py`
- `apps/api/app/observability/metrics.py`
- `apps/api/tests/`
- `apps/api/alembic/versions/`

Acceptance criteria:

- External apps can submit one normalized LLM event with an application API key.
- Accepted events appear in usage summaries and request listings.
- Rejected events do not create partial cost records.
- No raw secrets or sensitive prompt/document content are persisted.
- Existing gateway behavior remains unchanged.

## Phase 33: Proofbase application registration and configuration

Register Proofbase as a first-class client application of the Production AI Platform and define the safe configuration contract between the two repos.

Deliverables:

- Seed/dev data for a Proofbase project/application or documented admin setup steps.
- Dedicated placeholder API key for Proofbase local integration.
- Prompt and model route records that make Proofbase events filterable in the dashboard.
- `.env.example` additions for telemetry endpoint, API key, enabled flag, timeout, and redaction controls.
- Configuration docs for running both apps locally without real cloud resources.
- Tests or smoke checks proving the seed/setup is idempotent.

Relevant files:

- `apps/api/scripts/seed_dev_data.py`
- `apps/api/.env.example`
- `.env.example`
- `apps/api/app/schemas/admin.py`
- `apps/api/app/services/admin_config.py`
- `docs/deployment.md`
- `docs/gateway-flow.md`
- `docs/secrets-management.md`
- Proofbase target files:
  - `S:\github-repos\enterprise-knowledge-agent\.env.example`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\core\config.py`

Acceptance criteria:

- Proofbase has a distinct project/application identity in Production AI Platform.
- Local setup uses placeholders only and does not require real OpenAI or AWS credentials for telemetry validation.
- The dashboard can distinguish Proofbase traffic from existing demo app traffic.
- Proofbase remains fully functional if telemetry is disabled.

## Phase 34: Dashboard source-app filtering and event detail

Make external app telemetry visible and understandable in the Production AI Platform dashboard.

Deliverables:

- Dashboard filters for project/application/source app.
- Request/event detail panel that shows external request IDs and operation type.
- Usage summaries for Proofbase traffic.
- Cost, latency, token, status, and error display for externally ingested events.
- Empty states and error states for telemetry-only usage.
- Frontend tests for filters and event rendering.

Relevant files:

- `apps/web/components/dashboard.tsx`
- `apps/web/components/dashboard.test.tsx`
- `apps/web/components/dashboard.module.css`
- `apps/web/app/api/runtime-config/route.ts`
- `apps/web/package.json`
- `apps/api/app/api/usage.py`
- `apps/api/app/schemas/usage.py`
- `apps/api/app/services/usage.py`

Acceptance criteria:

- A user can filter the dashboard to only Proofbase telemetry.
- Event detail shows operation type, model, tokens, cost, latency, status, external ID, and error category.
- UI does not imply the platform performed Proofbase retrieval, citation validation, or permission checks.
- Existing dashboard behavior for normal gateway requests still works.

## Phase 35: Proofbase telemetry client and safe failure behavior

Add a small Proofbase client that sends telemetry events to Production AI Platform without affecting user-facing RAG behavior.

Deliverables:

- Proofbase telemetry client module.
- Config flags:
  - enabled/disabled
  - endpoint URL
  - API key
  - timeout
  - max metadata size
  - redaction behavior
- Best-effort submission that never fails the user query if the platform is down.
- Structured local log message when telemetry submission fails.
- Tests for disabled mode, successful submission, timeout/failure, redaction, and no-secret logging.

Relevant files:

- Proofbase target files:
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\core\config.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\logger.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\__init__.py`
  - `S:\github-repos\enterprise-knowledge-agent\scripts\`
  - `S:\github-repos\enterprise-knowledge-agent\README.md`
  - `S:\github-repos\enterprise-knowledge-agent\.env.example`
- Production reference files:
  - `apps/api/app/schemas/usage.py`
  - `docs/observability.md`

Acceptance criteria:

- Proofbase can send a synthetic telemetry event to Production AI Platform in local development.
- If Production AI Platform is unavailable, Proofbase queries still succeed.
- Telemetry payloads do not include full prompt text, full user questions, retrieved chunks, citations, document text, OpenAI keys, or platform API keys.
- Unit tests prove failure-isolation behavior.

## Phase 36: Proofbase query and streaming telemetry

Instrument Proofbase `/query` and `/query/stream` so chat-generation events are reported centrally.

Deliverables:

- Telemetry event emission after successful `/query` responses.
- Telemetry event emission after successful `/query/stream` completion.
- Failure telemetry for query errors where safe and useful.
- Mapping from Proofbase fields to the shared schema:
  - request ID
  - project ID
  - department ID
  - prompt name/version
  - model
  - input/output tokens
  - estimated cost
  - retrieval/generation/total latency
  - response type
  - pricing status
  - status/error category
- Tests for non-streaming query telemetry, streaming telemetry, and failure telemetry.

Relevant files:

- Proofbase target files:
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\main.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\generation\answer_generator.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\logger.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\tracing.py`
  - `S:\github-repos\enterprise-knowledge-agent\scripts\test_*.py`
- Production target files:
  - `apps/api/tests/`

Acceptance criteria:

- A normal Proofbase chat query creates a central Production AI Platform usage event.
- A streaming Proofbase chat query creates exactly one completed central usage event.
- Local Proofbase observability continues to work.
- Proofbase answer quality, citations, permission filtering, and memory behavior are unchanged.

## Phase 37: Proofbase auxiliary AI telemetry

Extend telemetry coverage beyond chat generation to other Proofbase AI call paths where the data can be captured safely.

Deliverables:

- AI Markdown cleanup telemetry.
- Query decomposition telemetry when OpenAI decomposition is used.
- Embedding generation telemetry for ingestion and retrieval where token/cost estimates can be represented honestly.
- Clear handling for operations with missing token usage or approximate estimates.
- Documentation of what is and is not billing-grade.
- Tests for cleanup telemetry and at least one embedding/decomposition telemetry path.

Relevant files:

- Proofbase target files:
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\projects\markdown_cleanup.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\reasoning\query_decomposer.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\embeddings\openai_embeddings.py`
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\projects\document_store.py`
  - `S:\github-repos\enterprise-knowledge-agent\docs\phase-16\cost-tracking.md`
  - `S:\github-repos\enterprise-knowledge-agent\README.md`
- Production target files:
  - `apps/api/app/services/pricing.py`
  - `apps/api/app/schemas/usage.py`
  - `docs/cost-analysis.md`

Acceptance criteria:

- AI Markdown cleanup calls appear centrally with model, tokens, cost, latency, and operation type.
- Embedding/decomposition telemetry is either implemented with honest estimates or explicitly documented as skipped until reliable usage data is available.
- Dashboard labels make clear which costs are estimated and which are missing/approximate.
- No uploaded document text or extracted Markdown is sent to Production AI Platform.

## Phase 38: Cross-repository automated validation

Add automated checks that prove the Proofbase-to-platform telemetry path works without relying on real OpenAI or cloud resources.

Deliverables:

- Production AI Platform tests for external event ingestion.
- Proofbase tests for telemetry client behavior.
- Cross-repo smoke script or documented local validation sequence.
- Mocked platform receiver test for Proofbase.
- Mocked Proofbase event fixture test for Production AI Platform.
- `docker compose config` validation for both repos when applicable.

Relevant files:

- `apps/api/tests/`
- `apps/web/components/dashboard.test.tsx`
- `docs/testing.md`
- `scripts/`
- Proofbase target files:
  - `S:\github-repos\enterprise-knowledge-agent\scripts\`
  - `S:\github-repos\enterprise-knowledge-agent\scripts\test_*.py`
  - `S:\github-repos\enterprise-knowledge-agent\docker-compose.yml`

Acceptance criteria:

- Tests can run without real OpenAI calls.
- Tests can run without AWS.
- Tests prove telemetry does not block Proofbase user workflows.
- Validation commands are documented for a developer new to cloud/devops.

## Phase 39: Browser end-to-end Proofbase telemetry demo

Verify the integration through the browser and local running apps.

Deliverables:

- Local run instructions for both apps.
- Browser validation checklist:
  - open Proofbase
  - send a query
  - open Production AI Platform dashboard
  - filter to Proofbase
  - inspect the resulting event
- Screenshot capture guidance with redaction rules.
- Playwright or browser-driven smoke verification where practical.
- Troubleshooting notes for ports, env vars, API keys, and unavailable services.

Relevant files:

- `docs/demo-script.md`
- `docs/dashboard-screenshots.md`
- `docs/testing.md`
- `README.md`
- `apps/web/components/dashboard.tsx`
- Proofbase target files:
  - `S:\github-repos\enterprise-knowledge-agent\apps\web\app\chat\ChatDemoClient.tsx`
  - `S:\github-repos\enterprise-knowledge-agent\apps\web\app\dev-admin\observability\page.tsx`
  - `S:\github-repos\enterprise-knowledge-agent\README.md`

Acceptance criteria:

- Browser validation proves a Proofbase interaction appears in Production AI Platform.
- The demo does not require Terraform, AWS resources, or production deployment.
- Screenshots avoid secrets, full prompts, full questions, document text, and sensitive content.
- Any skipped browser automation is documented with the blocker.

## Phase 40: Proofbase integration documentation and AgentOps handoff

Close the Proofbase integration sequence and prepare the next client-app integration with AgentOps Workflow Platform.

Deliverables:

- Final Proofbase integration docs.
- README update showing Proofbase as a connected client app.
- Portfolio/demo wording that preserves the Proofbase versus Production AI Platform boundary.
- Runbook notes for telemetry ingestion outages.
- Security notes for telemetry API keys and redaction.
- Reliability notes for best-effort telemetry.
- Observability notes for central dashboard interpretation.
- AgentOps integration readiness note that identifies reusable patterns and differences.

Relevant files:

- `README.md`
- `docs/architecture.md`
- `docs/observability.md`
- `docs/runbook.md`
- `docs/security-baseline.md`
- `docs/portfolio-demo-plan.md`
- `phases-progress.md`
- AgentOps reference files for the next sequence:
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\services\llm_client.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\services\cost_tracking.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\agent_step.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\cost_event.py`

Acceptance criteria:

- The docs can honestly claim Proofbase telemetry is centralized in Production AI Platform.
- The docs do not claim Production AI Platform performs Proofbase retrieval, citations, permission filtering, or benchmark evaluation.
- Telemetry outage behavior is documented as non-blocking.
- The next phase sequence can proceed to AgentOps without redesigning the event ingestion foundation.

## Phase 41: AgentOps contract and platform registration

Define AgentOps telemetry semantics and platform-side compatibility before touching AgentOps runtime code.

Deliverables:

- AgentOps operation taxonomy.
- Safe AgentOps metadata key list.
- Platform schema updates for AgentOps operation types.
- Local AgentOps project/application seed data and placeholder telemetry API key.
- AgentOps `.env.example` placeholder contract.
- Platform tests for AgentOps-shaped telemetry fixtures.
- Documentation updates linking to `docs/agentops-integration-plan.md`.

Relevant files:

- `docs/agentops-integration-plan.md`
- `docs/external-telemetry-contract.md`
- `docs/testing.md`
- `.env.example`
- `apps/api/app/schemas/usage.py`
- `apps/api/scripts/seed_dev_data.py`
- `apps/api/tests/`
- AgentOps reference files:
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\services\llm_client.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\services\cost_tracking.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\agent_step.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\cost_event.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\workflow_run.py`

Acceptance criteria:

- AgentOps event fixtures validate locally.
- Existing Proofbase telemetry fixtures still validate.
- Platform schema rejects prompts, generated outputs, workflow JSON, tool payloads, and sensitive fields.
- AgentOps can be registered as a distinct connected client app without redesigning ingestion.

## Phase 42: AgentOps telemetry client and switch

Add AgentOps-side configuration and a best-effort telemetry client.

Deliverables:

- `AGENTOPS_TELEMETRY_ENABLED=false` default.
- Telemetry endpoint, API key, timeout, metadata-size, and redaction config.
- Best-effort client with disabled mode, short timeout, failure isolation, and redacted diagnostics.
- AgentOps smoke script that sends one safe AgentOps-shaped event.
- Unit tests for disabled mode, success, receiver failure, timeout/failure isolation, and redaction.
- README and local setup docs for running AgentOps with or without Production AI Platform.

Relevant files:

- AgentOps target files:
  - `S:\github-repos\agentops-workflow-platform\.env.example`
  - `S:\github-repos\agentops-workflow-platform\README.md`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\core\config.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\observability\`
  - `S:\github-repos\agentops-workflow-platform\scripts\`
- Proofbase reference files:
  - `S:\github-repos\enterprise-knowledge-agent\apps\api\app\observability\platform_telemetry.py`
  - `S:\github-repos\enterprise-knowledge-agent\scripts\test_platform_telemetry_client.py`

Acceptance criteria:

- AgentOps runs normally when telemetry is disabled.
- AgentOps workflows are not blocked when Production AI Platform is down.
- No secrets, prompts, generated outputs, workflow JSON, or tool payloads are logged or sent.
- Client tests run without OpenAI, AWS, Terraform, or a running platform.

## Phase 43: AgentOps agent-step telemetry emission

Emit central telemetry for AgentOps agent steps.

Deliverables:

- Hook telemetry into the AgentOps agent-step completion/failure path.
- Emit one `agent_step` event per completed or failed model-backed step when model/token/latency data is available.
- Map workflow id, agent step id, agent name/type, step order, retry count, prompt version id, model, tokens, estimated cost, latency, status, and safe error category.
- Preserve AgentOps local cost tracking and workflow behavior.
- Tests for successful and failed step telemetry.

Relevant files:

- `S:\github-repos\agentops-workflow-platform\apps\api\src\models\agent_step.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\models\workflow_run.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\services\cost_tracking.py`
- AgentOps services that create/update agent steps
- AgentOps tests/scripts

Acceptance criteria:

- Completed agent steps appear centrally under `source_app=agentops`.
- Failed agent steps include safe status/error telemetry.
- AgentOps local workflow, retry, and cost behavior is unchanged.
- No workflow input/output JSON, prompt text, generated output, or tool payload is sent.

## Phase 44: AgentOps structured generation and workflow summary telemetry

Extend AgentOps coverage beyond basic step telemetry without double-counting cost.

Deliverables:

- Decide whether structured generation is represented as `agent_step` metadata or a distinct `structured_generation` operation.
- Add workflow summary telemetry only if it adds non-duplicative aggregate visibility.
- Document billing-estimate events versus aggregate summary events.
- Tests for duplicate prevention and cost-total consistency.

Relevant files:

- `S:\github-repos\agentops-workflow-platform\apps\api\src\services\llm_client.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\services\cost_tracking.py`
- `S:\github-repos\agentops-workflow-platform\apps\api\src\models\cost_event.py`
- AgentOps workflow run services/models
- Platform docs and tests

Acceptance criteria:

- Central dashboard does not double-count per-step and workflow-summary costs.
- Missing token/cost data is marked honestly as `unknown` or `unpriced`.
- Structured generation visibility does not expose JSON response bodies or schemas that contain sensitive data.

## Phase 45: AgentOps cross-repository automated validation

Add automated checks that prove the AgentOps-to-platform telemetry path without relying on real OpenAI or cloud resources.

Deliverables:

- Platform tests for AgentOps-shaped external telemetry.
- AgentOps mocked receiver tests.
- AgentOps telemetry smoke script.
- Cross-repo documented validation sequence.
- Docker Compose config validation for both repos where applicable.

Relevant files:

- `apps/api/tests/`
- `docs/testing.md`
- `scripts/`
- AgentOps target files:
  - `S:\github-repos\agentops-workflow-platform\scripts\`
  - `S:\github-repos\agentops-workflow-platform\tests\`
  - `S:\github-repos\agentops-workflow-platform\docker-compose.yml`

Acceptance criteria:

- Tests can run without real OpenAI calls.
- Tests can run without AWS, Terraform, or deployments.
- Mocked platform failures do not break AgentOps workflows.
- Validation commands are documented for a developer new to cloud/devops.

## Phase 46: Browser end-to-end AgentOps telemetry demo

Verify the AgentOps integration through local running apps and the browser dashboard.

Deliverables:

- Local run instructions for Production AI Platform and AgentOps on non-conflicting ports.
- Browser validation checklist:
  - run or simulate an AgentOps workflow
  - open Production AI Platform dashboard
  - filter to `agentops`
  - inspect the resulting agent-step event
- Screenshot capture guidance with redaction rules.
- Troubleshooting notes for ports, env vars, API keys, unavailable services, and dashboard refresh.

Relevant files:

- `docs/agentops-integration-plan.md`
- `docs/dashboard-screenshots.md`
- `docs/testing.md`
- `README.md`
- `apps/web/components/dashboard.tsx`
- AgentOps README and web/API local run docs

Acceptance criteria:

- Browser validation proves AgentOps traffic appears in Production AI Platform.
- Demo does not require Terraform, AWS resources, or production deployment.
- Screenshots avoid secrets, prompts, generated outputs, workflow JSON, tool payloads, and sensitive content.

## Phase 47: AgentOps integration closeout

Close the second client-app integration and update the portfolio story.

Deliverables:

- Final AgentOps integration docs.
- README update showing Proofbase and AgentOps as connected telemetry clients.
- Portfolio/demo wording that preserves app boundaries.
- Runbook notes for AgentOps telemetry ingestion outages.
- Security notes for telemetry keys and workflow payload redaction.
- Reliability notes for best-effort AgentOps telemetry.
- Observability notes for central dashboard interpretation.

Relevant files:

- `README.md`
- `docs/architecture.md`
- `docs/observability.md`
- `docs/runbook.md`
- `docs/security-baseline.md`
- `docs/portfolio-demo-plan.md`
- `docs/agentops-integration-plan.md`
- `phases-progress.md`

Acceptance criteria:

- Docs can honestly claim AgentOps telemetry is centralized in Production AI Platform.
- Docs do not claim Production AI Platform executes AgentOps workflows, owns prompts, inspects generated outputs, or handles tool payloads.
- Telemetry outage behavior is documented as non-blocking.
- Proofbase and AgentOps are described as distinct connected client apps with different domains.

## Java conversion and AWS release continuation

Phases 48-69 implement the user-approved Java Spring Boot conversion and remaining AWS/public-release work. Historical phases remain unchanged. Follow AGENTS.md for every phase and docs/java-aws-implementation-plan.md for cross-phase design. Cloud mutation and publication phases have explicit approval gates.

## Phase 48: Java conversion and AWS release roadmap

Deliverables:

- Record the approved Java direction, AWS scope, migration boundaries, phase order, acceptance evidence, and human gates.

Relevant files:

- AGENTS.md, PROJECT_SPEC.md, phases.md, phases-progress.md, README.md, docs/java-aws-implementation-plan.md

Acceptance criteria:

- Historical phases 1-47 remain intact; the new sequence has exactly one current phase; Azure is superseded; implementation and live validation are explicitly distinguished.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 49: Backend compatibility contract baseline

Deliverables:

- Export the current HTTP/OpenAPI contract; inventory response/error formats, SQL constraints, metric names, and safe telemetry fixtures. Add reproducible contract checks and document intentional security changes.

Relevant files:

- contracts/, scripts/, apps/api/tests/, docs/java-migration-contract.md

Acceptance criteria:

- Baseline generation is deterministic and contains synthetic data only. Coverage includes gateway success/failure, usage filters, admin configuration, telemetry duplicates/conflicts/redaction, decimal serialization, timestamps, and non-billable summaries.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 50: Spring Boot build and service foundation

Deliverables:

- Create apps/api-java with Java 21, a pinned stable Spring Boot release, Maven Wrapper, formatting/static checks, MVC, validation, and narrowly exposed operational endpoints. Add Java verification to CI while Python remains the runtime.

Relevant files:

- apps/api-java/, .github/workflows/ci.yml, docs/testing.md

Acceptance criteria:

- Wrapper integrity and dependencies are checked; clean Maven verify passes locally and in CI; health and JSON/error boundary tests pass; no runtime cutover or real provider call occurs.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 51: PostgreSQL persistence and migration handover

Deliverables:

- Implement database mappings/repositories, transactions, Flyway SQL migrations, and deterministic synthetic seeds. Define a verified baseline/adoption procedure for an existing Alembic database.

Relevant files:

- apps/api-java/, contracts/, docs/database-migration-handover.md

Acceptance criteria:

- Fresh PostgreSQL and a copy of the Alembic schema reach the same schema without loss. UUIDs, JSONB, numeric precision, indexes, uniqueness, and foreign keys match. No auto-DDL, automatic downgrade, blind baselining, or dual migration owner.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 52: Java gateway and model routing

Deliverables:

- Port API-key hashing and active application checks, prompt/default-route selection, mock provider, timeout/retry behavior, durable request/cost recording, and bounded gateway validation.

Relevant files:

- apps/api-java/, contracts/

Acceptance criteria:

- HTTP contract tests cover success, missing/invalid/revoked keys, inactive applications, missing routes/prompts, transient failures, timeouts, and decimal cost values. External calls are mocked; provider inputs/outputs are not logged.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 53: Java Proofbase and AgentOps telemetry ingestion

Deliverables:

- Port ingestion validation, metadata allowlists, normalization, event attribution, idempotency, duplicate conflicts, pricing status, and workflow-summary treatment.

Relevant files:

- apps/api-java/, contracts/, scripts/

Acceptance criteria:

- Both client fixture suites pass without changing client payloads. Concurrent duplicate submissions create one event and at most one cost record; conflicting duplicates return the documented conflict; unsafe fields are rejected; summaries cannot double-count cost; metric labels are bounded.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 54: Java usage and operator configuration APIs

Deliverables:

- Port usage summary/request/error/scope queries and filters, prompt/model CRUD/activation, and audit records. Preserve the frontend response contract.

Relevant files:

- apps/api-java/, contracts/, apps/web/components/

Acceptance criteria:

- Equivalent seeded requests yield equivalent summaries and lists. Filtering, ordering, pagination caps, nulls, decimal strings, and audit behavior are covered. Existing frontend tests continue to pass; operator endpoints remain locally bound until Phase 55 access controls exist.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 55: Operator authorization and application key lifecycle

Deliverables:

- Implement OIDC-based operator authentication, viewer/operator roles, server-side project grants, and project-scoped key creation/revocation with verified audit actors. Integrate dashboard authentication and an explicit isolated synthetic demo mode.

Relevant files:

- apps/api-java/, apps/web/, docs/security-baseline.md, docs/security-audit.md

Acceptance criteria:

- Unauthenticated or unauthorized callers cannot read cross-project data or mutate settings; spoofed actor headers are ignored; machine API keys cannot grant operator access. OIDC issuer/audience/expiry/signature checks, CSRF/session protections where applicable, key lifecycle, and negative authorization tests pass. Local identity tests need no cloud account.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 56: Distributed limits and dependency-aware readiness

Deliverables:

- Implement atomic Redis limits shared across replicas, telemetry admission controls, bounded body/metadata/query sizes, timeouts, correct readiness/liveness separation, and graceful draining.

Relevant files:

- apps/api-java/, apps/api-java/src/test/, docs/runbook.md

Acceptance criteria:

- Multi-instance/concurrent limiter tests pass. Invalid-key spray is bounded. Redis/database outages return the documented safe errors; readiness observes required dependencies with timeouts; liveness survives dependency failure; retry/shutdown budgets are tested and documented.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 57: Java metrics logs and traces

Deliverables:

- Implement Actuator/Micrometer/OpenTelemetry instrumentation, safe structured logs, bounded request IDs, tracing propagation, and application metrics compatible with the existing dashboards or explicitly versioned replacements.

Relevant files:

- apps/api-java/, infra/monitoring/, docs/observability.md

Acceptance criteria:

- One request has correlated request/trace IDs and expected gateway spans. Metric labels exclude arbitrary client strings and identifiers. Redaction tests cover error paths; health/metrics exposure is restricted; dashboard queries are checked against actual Java metric output.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 58: Java Docker Compose and Helm runtime cutover

Deliverables:

- Build non-root JVM images, update local startup/migration/seed scripts and Helm/Kubernetes runtime configuration, and make Java the default API only after parity and authorization gates pass.

Relevant files:

- apps/api-java/Dockerfile*, docker-compose.yml, Makefile, infra/helm/, infra/k8s/, docs/local-portfolio-stack.md

Acceptance criteria:

- Fresh Compose startup, migrations, Java API, dashboard login/demo, gateway, and both telemetry clients pass end-to-end checks. JVM resources, startup/readiness probes, shutdown, TLS database/Redis connections, and writable paths are verified. Python is retained only as an explicit reference until removal is validated.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 59: AWS infrastructure validation and bootstrap boundaries

Deliverables:

- Strengthen Terraform validation and all-environment Helm/schema checks. Separate cluster-wide operators/stores/controller installation from namespace-scoped app releases; document private EKS runner/DNS connectivity and state bootstrap.
- Investigate the pinned v3.5.0 controller with Terraform-owned ALB/listeners/rules/security groups/target groups and restricted TargetGroupBinding registration. Remove Ingress writes instead of activating the proposed KSV-0056 exception. Adopt the design only after controller lifecycle, Kubernetes RBAC/admission denials and AWS permission boundaries are validated; document limitations and remaining cloud validation gates.

Relevant files:

- infra/terraform/, infra/helm/, infra/k8s/, .github/workflows/ci.yml, docs/deployment.md

Acceptance criteria:

- All AWS environment roots fmt/validate; all Helm values render and validate with CRD schemas. Required EKS add-ons and NetworkPolicy enforcement are explicit; cluster-scoped resources no longer require app deployer privilege escalation. Static validation creates no AWS resources.
- Scanner success alone is insufficient: exercise registration/deregistration, readiness, restart/deletion/finalizer recovery and rejected unauthorized operations on disposable Kubernetes with the pinned controller. Distinguish local AWS protocol fixtures from real IAM and ALB data-plane evidence. The scanner exception remains inactive.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 60: Java supply chain and CI release eligibility

Deliverables:

- Complete Java dependency/image/IaC/history-secret gates, SBOM generation, pinned tooling, and exact-revision release eligibility. Preserve frontend validation and contract tests while removing obsolete Python runtime gates only after cutover.

Relevant files:

- .github/workflows/ci.yml, apps/api-java/pom.xml, scripts/, docs/ci-cd.md

Acceptance criteria:

- Clean CI includes non-skipped PostgreSQL/Redis integration tests, frontend checks, runtime image builds/scans, Java audits, and infrastructure checks. Fork pull requests receive no deployment credentials. A failed or unverified revision cannot become release-eligible.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 61: AWS immutable promotion migrations and rollback

Deliverables:

- Refactor dev/staging/prod/rollback workflows to build and scan once, promote by verified digest, use scoped publisher/migration/application OIDC roles, run controlled migration jobs, and test functional deployment health. Verify OCI copy compatibility before adoption; bind packaged charts/environment values and staged receipts to CI provenance. Manual preflight is read-only; keep cloud jobs explicitly held until environment approval. Rollback verifies live schema without database downgrade.

Relevant files:

- .github/workflows/deploy-*.yml, .github/workflows/rollback.yml, infra/helm/, docs/deployment.md

Acceptance criteria:

- Dry-run/static tests reject invalid refs/digests and incompatible rollback inputs. Private runner connectivity and bootstrap permissions are explicit. Prod requires protected environment approval; database migrations have one owner; application rollback never auto-downgrades the database.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 62: Runnable monitoring stack and supported log collection

Deliverables:

- Codify a local monitoring profile and EKS bootstrap package for Prometheus, Grafana, Loki, Alloy, OpenTelemetry Collector, trace storage, exporters, and Alertmanager.

Relevant files:

- infra/monitoring/, docker-compose*.yml, docs/observability.md, docs/dashboard-screenshots.md

Acceptance criteria:

- Synthetic Java traffic produces non-empty dashboards, searchable logs/traces, and a fired/resolved local alert. Replace EOL Promtail, verify bounded cardinality and retention, provision durable storage appropriately, and protect monitoring access. Cloud installation remains gated.
- Audit every pinned monitoring image against the existing high/critical vulnerability and secret policy before adoption. A successful runtime rehearsal or clean manifest scan cannot substitute for image eligibility. Record unresolved upstream image findings as a phase blocker; do not silently add exceptions or adopt unverified dependency overrides.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 63: Local resilience recovery and cost rehearsal

Deliverables:

- Exercise disposable local load, dependency outages, restart/rolling release, compatible rollback, and PostgreSQL backup/restore. Add reproducible evidence and response runbooks; refresh AWS sizing assumptions.

Relevant files:

- scripts/, docs/backup-restore.md, docs/incident-response.md, docs/cost-analysis.md, docs/phase-reviews/

Acceptance criteria:

- Record measured local latency/error behavior, alert resolution, restore time and recovered records; mark local evidence distinctly from AWS RTO/RPO. No existing database is deleted. Budgets are documented as alerts, with quotas/retention/scaling as separate controls.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 64: Public repository and isolated demo preparation

Deliverables:

- Run a full-history secret review and dependency/security audit, prepare a license choice, security reporting/contribution guidance, synthetic demo screenshots/video instructions, draft release notes, and honest README claims.

Relevant files:

- README.md, SECURITY.md, CONTRIBUTING.md, docs/assets/, docs/portfolio-demo-plan.md

Acceptance criteria:

- Resolve publication blockers and record remaining decisions; choose the license with the owner before release. Demo data is isolated, admin writes are protected, paid provider calls remain disabled, and no customer telemetry is exposed. Do not change repository visibility or publish a release in this phase.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 65: AWS launch preflight and approval package

Deliverables:

- Prepare the concrete dev launch package: validated Terraform/Helm artifacts, current cost estimate, region/quota/access requirements, state/secret/bootstrap inputs, runner connectivity, monitoring/backup plan, and rollback commands.

Relevant files:

- docs/aws-launch-checklist.md, docs/cost-analysis.md, docs/deployment.md

Acceptance criteria:

- All locally executable checks pass. Record missing subscription/account/domain inputs without inventing values. Any authenticated plan remains read-only and uses safe state handling. Present a specific resource/cost/change package for approval before apply, real secrets, or DNS/TLS mutation.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 66: Approved AWS dev deployment and operational evidence

Deliverables:

- After explicit approval and required access, bootstrap AWS dev, install operators/monitoring, deploy the Java release, and run functional smoke and controlled operational checks.

Relevant files:

- AWS dev environment, docs/phase-reviews/, docs/aws-launch-checklist.md

Acceptance criteria:

- Real EKS deployment, scoped OIDC, secret synchronization, HTTPS, gateway/telemetry/auth, dashboards/traces, backup, and rollback are verified. Record actual cloud evidence and cost; do not claim production readiness from static checks.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 67: Approved staging promotion and recovery exercise

Deliverables:

- After environment-specific approval, promote the same verified image digest to staging and rehearse recovery and migration compatibility.

Relevant files:

- AWS staging environment, docs/backup-restore.md, docs/deployment.md

Acceptance criteria:

- Staging uses separate secrets and data, passes authorization/load checks, demonstrates safe rollback and a restore into a new approved target, and records measured RTO/RPO and residual risks.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 68: Approved production or public demo launch

Deliverables:

- Obtain explicit approval for the selected production/public-demo footprint and real DNS/TLS changes, then release through protected workflows.

Relevant files:

- AWS approved environment, docs/incident-response.md, docs/deployment.md

Acceptance criteria:

- Only an approved digest is released; operator access and synthetic demo boundaries work; spending limits/alerts and monitoring owners are configured; post-launch checks and rollback readiness are recorded. Public demo does not imply customer-production approval.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.

## Phase 69: Approved public repository release and closeout

Deliverables:

- After explicit publication authorization, finalize the chosen license and sanitized portfolio assets, publish the verified release, and change repository visibility if requested.

Relevant files:

- README.md, release assets, GitHub repository settings, phases-progress.md

Acceptance criteria:

- History/security review is current, released code matches successful CI, claims match measured evidence, no secrets/customer data are public, and all implemented phases have pushed commits and completed reviews. Optional provider work is clearly separate.
- Follow the per-phase validation, conventional commit, push, pushed-commit review, separate fix-commit, and phase-review loop in AGENTS.md.
