# phases.md

# Production AI Platform / LLMOps Infrastructure Platform Roadmap

This roadmap is designed for Codex to implement phases sequentially as an autonomous phase-based engineering agent. Each phase should be small enough for a focused commit and review, while the full project becomes a strong DevOps/cloud portfolio piece.

Codex should complete the current `In Progress` phase, commit and push it, write the phase review, then move automatically to the next phase unless a stop condition in `AGENTS.md` requires human approval or a blocker prevents safe progress.

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

- CI runs on pull requests.
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
