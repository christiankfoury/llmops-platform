# AGENTS.md

## Project

Production AI Platform / LLMOps Infrastructure Platform.

This repository is a portfolio-grade DevOps/cloud project connected to AI engineering. The product is a lightweight LLM gateway and usage dashboard, but the main value is the production infrastructure around it: Kubernetes, Terraform, Helm, CI/CD, observability, secrets, reliability, staged environments, rollback, and cost controls.

## Portfolio relationship and scope boundary

This project complements Proofbase, which is the permission-aware enterprise RAG application. Keep the distinction clear in code, docs, README claims, and demo scripts:

- Proofbase proves the AI product layer: document ingestion, scoped retrieval, citations, permission safety, memory boundaries, and benchmark-driven answer quality.
- Production AI Platform proves the operations layer: LLM gateway, prompt/model routing, API keys, usage tracking, cost/latency/error monitoring, CI/CD, Kubernetes, Terraform, observability, secrets, rollback, and runbooks.

Do not duplicate Proofbase's advanced RAG features in this repository. A future integration can describe Proofbase as a client app that calls this platform's LLM gateway for centralized routing, cost, latency, tracing, and operational controls.

## Target portfolio claim

By the end of the project, the repository should credibly support this claim:

> Built a production-grade AI platform on AWS using Kubernetes, Terraform, Helm, GitHub Actions, Prometheus, Grafana, Loki, OpenTelemetry, managed PostgreSQL, Redis, external secret management, staged deployments, rollback workflows, request tracing, cost monitoring, and reliability runbooks.

## Default technical choices

Use these defaults unless a phase explicitly changes them:

- Cloud: AWS.
- Kubernetes: Amazon EKS.
- Container registry: Amazon ECR.
- Database: Amazon RDS PostgreSQL.
- Cache/queue: Amazon ElastiCache Redis where cloud-managed infrastructure is required; local Redis for development.
- Secrets: AWS Secrets Manager through External Secrets Operator.
- Backend: FastAPI, Python, SQLAlchemy, Alembic, Pydantic.
- Frontend: Next.js, TypeScript, Tailwind, shadcn/ui where useful.
- Database: PostgreSQL.
- Local development: Docker Compose.
- Observability: OpenTelemetry, Prometheus, Grafana, Loki.
- CI/CD: GitHub Actions.
- Packaging: Docker images and Helm chart.
- GitOps optional stretch: Argo CD.

## Repository structure target

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
      Chart.yaml
      values.yaml
      values-dev.yaml
      values-staging.yaml
      values-prod.yaml
      templates/

  k8s/
    base/
    overlays/
      dev/
      staging/
      prod/

.github/
  workflows/
    ci.yml
    deploy-dev.yml
    deploy-staging.yml
    deploy-prod.yml
    rollback.yml

docs/
  architecture.md
  deployment.md
  runbook.md
  incident-response.md
  cost-analysis.md
  security-baseline.md
  portfolio-demo-plan.md
```

## Core product requirements

The application should implement a realistic but scoped LLMOps platform:

- LLM gateway API.
- Project/app API keys.
- Prompt versioning.
- Model routing.
- Request logging.
- Cost tracking.
- Latency tracking.
- Error/failure tracking.
- Rate limiting.
- Audit logs.
- Usage dashboard.
- Cost dashboard.
- Latency dashboard.
- Error dashboard.
- Admin/project dashboard.

Do not overbuild product features at the expense of infrastructure quality. The app is the payload; the infrastructure is the star.

## Required Codex workflow for every phase

For each phase in `phases.md`, follow this exact loop:

1. Read:
   - `PROJECT_SPEC.md`
   - `phases.md`
   - `phases-progress.md`
   - Relevant existing code and docs.
2. Identify the current phase from `phases-progress.md`.
3. Write a concise implementation plan before editing.
4. Implement only the current phase scope.
5. Add or update tests where appropriate.
6. Run the relevant checks locally:
   - Backend lint/tests/type checks when backend changes exist.
   - Frontend lint/tests/type checks when frontend changes exist.
   - Docker build checks when Docker changes exist.
   - Terraform format/validate when Terraform changes exist.
   - Helm lint/template checks when Helm changes exist.
   - Kubernetes manifest validation when manifests change.
7. Fix issues found by checks.
8. Update documentation affected by the phase.
9. Update `phases-progress.md`:
   - Mark the current phase as completed.
   - Add implementation notes.
   - Add test/check results.
   - Set the next phase to `In Progress`.
10. Create a git commit with a detailed conventional commit message.
11. Push the branch.
12. Perform a self-review and report:
   - What changed.
   - Files changed.
   - Tests/checks run.
   - Security considerations.
   - Infra/deployment considerations.
   - Whether implementation stayed within phase scope.
   - Risks or follow-up items.
13. Proceed to the next phase only after the current phase is complete.

## Commit message format

Use conventional commits.

Examples:

```text
docs(project): define production AI platform scope

feat(api): add LLM gateway request logging

feat(infra): provision EKS foundation with Terraform

ci(pipeline): add image scanning and build workflow

chore(release): add Helm rollback workflow
```

Each commit body should include:

```text
Summary:
- ...

Validation:
- ...

Security:
- ...

Phase:
- Phase N: <title>
```

## Pull request / review format

Every completed phase report should use this format:

```text
## Phase N Review

### Summary
- ...

### Scope Check
- In scope:
- Out of scope avoided:

### Files Changed
- ...

### Validation
- Command:
- Result:

### Security Review
- Secrets:
- Auth:
- IAM/RBAC:
- Network:
- Supply chain:

### Reliability Review
- Health checks:
- Rollback:
- Failure handling:

### Observability Review
- Logs:
- Metrics:
- Traces:
- Dashboards:

### Risks / Follow-ups
- ...

### Next Phase
- Phase N+1: ...
```

## Scope discipline

Do not combine multiple phases into one large implementation. If a later-phase feature is needed, add a TODO or small interface stub only when necessary.

Examples:

- In Phase 2, create simple placeholders for metrics, but do not implement full Prometheus/Grafana.
- In Phase 3, store request logs and cost estimates, but do not build the final dashboard.
- In Phase 5, create Terraform modules, but do not add every security hardening control until the security phase.
- In Phase 9, add observability, but do not perform final portfolio polish.

## Security rules

Never commit secrets.

Do not create `.env` files with real credentials. Only commit `.env.example`.

Use placeholders for:

- AWS account IDs.
- domain names.
- API keys.
- database passwords.
- OpenAI keys.
- GitHub tokens.

Use least privilege whenever IAM is introduced. Avoid wildcard permissions unless justified in comments and docs.

When writing Terraform:

- Avoid hardcoded secrets.
- Use remote state placeholders/docs rather than committing real backend credentials.
- Add tags to cloud resources.
- Make environments explicit.
- Keep prod defaults conservative.

When writing Kubernetes manifests:

- Use non-root containers where possible.
- Add resource requests and limits.
- Add readiness and liveness probes.
- Do not put plaintext secrets in manifests.
- Use NetworkPolicies once the phase calls for them.
- Use External Secrets or references to cloud secrets for sensitive values.

## Reliability rules

Production-facing workloads should eventually include:

- Readiness probes.
- Liveness probes.
- Graceful shutdown.
- Rolling update strategy.
- Resource requests/limits.
- HorizontalPodAutoscaler.
- PodDisruptionBudget.
- Deployment rollback documentation.
- Database backup/restore documentation.
- Incident response runbook.
- Alerting rules.

Add these gradually according to the phase roadmap.

## Observability rules

Use structured logs with request IDs.

Every LLM gateway request should eventually emit:

- request ID
- project/app ID
- prompt version
- selected model
- latency
- status code
- error category if failed
- token usage when available
- estimated cost
- trace ID

Metrics should eventually include:

- request count
- error count
- latency histogram
- estimated cost total
- token usage total
- model routing count
- rate limit rejections
- API key auth failures

Traces should cover:

- API request
- authentication
- prompt lookup
- model routing
- provider call
- database write
- response serialization

## Testing expectations

Backend:

- Unit tests for services.
- Integration tests for API routes.
- Database migration tests where practical.
- Mock external LLM provider calls.

Frontend:

- Type checks.
- Lint checks.
- Component tests where practical.
- Basic dashboard rendering tests.

Infrastructure:

- `terraform fmt`
- `terraform validate`
- `helm lint`
- `helm template`
- Kubernetes manifest validation where available.
- Docker image build checks.
- CI workflow syntax sanity checks where practical.

## Definition of done

A phase is done only when:

- Its deliverables are implemented.
- Tests/checks pass or failures are clearly documented.
- Documentation is updated.
- `phases-progress.md` is updated.
- Commit is created with a detailed message.
- Self-review is completed.
- No unrelated phases were implemented prematurely.

## Important non-goals

This project is not primarily about building the most advanced LLM application.

Avoid spending too much time on:

- Complex agent orchestration.
- Fancy chat UI.
- Multi-modal AI features.
- Large custom evaluation systems.
- Huge prompt libraries.
- Advanced RAG, vector retrieval, citation validation, document ingestion, or benchmark-driven answer evaluation; those belong in Proofbase.

Prioritize infrastructure excellence.

## Final recruiter-facing story

The final README and demo should make these points obvious within the first minute:

- This is a production AI platform, not a toy app.
- It runs locally and on Kubernetes.
- Cloud infrastructure is managed with Terraform.
- Releases are packaged with Helm.
- CI/CD is automated with GitHub Actions.
- Environments are separated.
- Secrets are not hardcoded.
- Observability is built in.
- Rollback and incident response are documented.
- Costs, latency, and failures are measurable.
