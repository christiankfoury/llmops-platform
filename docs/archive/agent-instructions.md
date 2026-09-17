> Historical document. Current behavior and scope are described in the [documentation index](../README.md).

# AGENTS.md

## Project

Production AI Platform / LLMOps Infrastructure Platform.

This repository is a portfolio-grade DevOps/cloud project connected to AI engineering. The product is a lightweight LLM gateway and usage dashboard, but the main value is the production infrastructure around it: Kubernetes, Terraform, Helm, CI/CD, observability, secrets, reliability, staged environments, rollback, and cost controls.

## Portfolio relationship and scope boundary

This project complements Proofbase, which is the permission-aware enterprise RAG application, and AgentOps Workflow Platform, which is the agent workflow/orchestration application. Keep the distinction clear in code, docs, README claims, and demo scripts:

- Proofbase proves the AI product layer: document ingestion, scoped retrieval, citations, permission safety, memory boundaries, and benchmark-driven answer quality.
- AgentOps proves the agent workflow layer: workflow runs, agent steps, structured generation, retries, tool/agent categories, per-step costs, and workflow observability.
- Production AI Platform proves the operations layer: LLM gateway, prompt/model routing, API keys, usage tracking, cost/latency/error monitoring, CI/CD, Kubernetes, Terraform, observability, secrets, rollback, and runbooks.

Do not duplicate Proofbase's advanced RAG features in this repository. Proofbase is currently connected as a telemetry-first client app; a later gateway-routing integration can describe Proofbase as a client app that calls this platform's LLM gateway for centralized routing, cost, latency, tracing, and operational controls.

Do not duplicate AgentOps workflow orchestration features in this repository. AgentOps may connect as a client app that sends centralized LLM usage telemetry for workflow and agent-step operations. Production AI Platform should not execute AgentOps workflows, own AgentOps prompts, inspect generated outputs, or handle tool payloads.

## AgentOps integration guidance

When implementing the AgentOps Workflow Platform integration:

- Use the completed Proofbase integration as the reference implementation and test template.
- Do not copy Proofbase RAG-specific names or metadata into AgentOps.
- Read AgentOps' actual files before designing each phase:
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\services\llm_client.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\services\cost_tracking.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\agent_step.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\cost_event.py`
  - `S:\github-repos\agentops-workflow-platform\apps\api\src\models\workflow_run.py`
- Add an explicit switch so AgentOps can run with or without Production AI Platform:
  - `AGENTOPS_TELEMETRY_ENABLED=false`
  - `AGENTOPS_TELEMETRY_ENDPOINT=http://localhost:8000/v1/usage/llm-events`
  - `AGENTOPS_TELEMETRY_API_KEY=agentops-local-placeholder-key-not-a-secret`
  - `AGENTOPS_TELEMETRY_TIMEOUT_SECONDS=2`
  - `AGENTOPS_TELEMETRY_MAX_METADATA_BYTES=2048`
  - `AGENTOPS_TELEMETRY_REDACT_CONTENT=true`
- Keep telemetry best-effort: platform outages, timeouts, or validation failures must not break AgentOps workflows.
- Send operational metadata only: workflow/step IDs, agent name/type, step order, retry count, model, tokens, latency, estimated cost, status, and safe error categories.
- Do not send prompts, generated outputs, workflow input/output JSON, tool arguments, tool results, raw provider payloads, API keys, provider credentials, or user/customer data.
- Keep central cost reporting honest. Avoid double-counting per-step and workflow-summary costs; mark missing or aggregate-only data as `unknown` or `unpriced` where appropriate.
- Implement AgentOps phases sequentially from `docs/agentops-integration-plan.md` and `phases.md`.

## Target portfolio claim

By the end of the project, the repository should credibly support this claim:

> Built and demonstrated a production-style LLMOps platform in one AWS dev/demo environment using Java, Kubernetes, Terraform, Helm, GitHub Actions, Prometheus, Grafana, Loki, OpenTelemetry, managed PostgreSQL, Redis, external secrets, request tracing, cost monitoring, and tested release/rollback and local backup/restore procedures.

Use this target claim only after the approved AWS demonstration and its evidence exist. Staging/production configurations are optional, statically validated designs unless separately deployed and tested.

## Default technical choices

Use these defaults unless a phase explicitly changes them:

- Cloud: AWS.
- Kubernetes: Amazon EKS.
- Container registry: Amazon ECR.
- Database: Amazon RDS PostgreSQL.
- Cache/queue: Amazon ElastiCache Redis where cloud-managed infrastructure is required; local Redis for development.
- Secrets: AWS Secrets Manager through External Secrets Operator.
- Backend target: Java 21, Spring Boot MVC, Maven Wrapper, Spring Data JPA/Hibernate, Flyway, Jakarta Validation.
- Migration baseline: FastAPI/Python remains the reference runtime until the Java compatibility and cutover phases pass.
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

## Autonomous phase loop

The active continuation is the Java conversion and AWS release sequence in `docs/java-aws-implementation-plan.md` and phases 48-69. AWS remains the cloud target. Preserve phases 1-47 as historical completion evidence. Implement Java in `apps/api-java` and retain `apps/api` as the reference until the explicit runtime cutover phase. For Java changes, run Maven verification, formatting/static checks, and required PostgreSQL/Redis integration tests; do not count skipped database tests as successful validation. Do not start an Azure migration. Never run two migration owners or enable automatic destructive schema updates.

Codex should operate as an autonomous phase-based engineering agent.

Continue implementing phases sequentially until all phases are completed or a stop condition occurs.

For each phase:

1. Read `AGENTS.md`, `PROJECT_SPEC.md`, `phases.md`, and `phases-progress.md`.
2. Find the current phase marked as `In Progress` in `phases-progress.md`.
3. Read the deliverables and acceptance criteria for that phase in `phases.md`.
4. Write a concise implementation plan.
5. Implement only the current phase scope.
6. Do not implement future phases early unless a minimal placeholder is required for the current phase to work.
7. Add or update tests/checks where appropriate.
8. Run safe validation commands:
   - Backend lint/tests/type checks when backend changes exist.
   - Frontend lint/tests/type checks when frontend changes exist.
   - Docker build checks when Docker changes exist.
   - Terraform format/validate when Terraform changes exist.
   - Helm lint/template checks when Helm changes exist.
   - Kubernetes manifest validation when manifests change.
9. Fix validation issues.
10. Update documentation affected by the phase.
11. Update `phases-progress.md`:
   - Mark the completed phase as `Completed`.
   - Record implementation notes.
   - Record validation results.
   - Record security, reliability, and observability notes where relevant.
   - Mark the next phase as `In Progress`.
12. Commit with a detailed conventional commit message.
13. Push the commit to `main`.
14. Review the pushed commit and identify the top actionable findings:
   - Bugs or correctness issues.
   - Security issues.
   - Reliability issues.
   - Observability gaps.
   - Missing validation.
   - Scope discipline problems.
   - Documentation gaps.
15. Fix each top finding in a separate follow-up commit.
16. Run the relevant validation for each fix commit.
17. Push each fix commit to `main`.
18. Repeat the post-commit review/fix loop until no top findings remain or a stop condition occurs.
19. Write a phase review covering:
   - Summary.
   - Files changed.
   - Validation.
   - Security.
   - Reliability.
   - Observability.
   - Scope discipline.
   - Risks.
   - Next phase.
20. Move to the next phase automatically and repeat.

Do not wait for human approval between normal app, code, documentation, local Docker, CI, test, Helm template, or static validation phases.

### Owner continuation override: deferred Phase 62 (2026-09-08)

The owner deferred monitoring vulnerability fixes and custom third-party rebuilds
and requested continuation of the remaining implementation toward AWS setup.
This scoped override takes precedence over the normal sequential/blocker rules:

- Keep Phase 62 **Blocked**, incomplete and not release-eligible. Preserve the
  runnable monitoring deliverable, local prototype and vulnerability backlog;
  do not automatically restart its fixes or rebuilds, suppress findings, or
  interpret deferral as deployment risk acceptance.
- Select Phase 63 as the active continuation, then proceed through the independent
  preparation scopes of Phases 64 and 65. Their revised acceptance criteria in
  `phases.md` explicitly carry monitoring-dependent checks into the Phase 62 /
  pre-Phase 66 blocker list. Unexecuted checks never count as passes.
- Finish the phase commit/push/review loop and all mandatory CI for each completed
  preparation phase. Repair ordinary CI/tool availability failures separately;
  those are not covered by the monitoring vulnerability deferral.
- Phase 65 may finish an honest launch preparation package with a **blocked launch
  decision**. It cannot declare deployment readiness while Phase 62 or required
  CI remains unresolved. Stop before Phase 66 for AWS setup and explicit approval;
  all other existing approval gates still apply earlier when encountered.
- Read `docs/next-chat-handoff.md` before continuation. Preserve the existing dirty
  Phase 62 working tree. Use an isolated checkout from main for independent work
  where practical; do not discard, automatically commit or adopt the prototype,
  custom images or rebuild recipes as part of another phase.

### Portfolio completion scope (owner direction, 2026-09-08)

Use `docs/portfolio-completion-plan.md` and the revised phase criteria to keep the
remaining work bounded. Demonstrate each important capability, retain evidence
and document limitations. Do not expand the remaining phases into an open-ended
security, benchmarking or third-party distribution maintenance project.

- Phase 63: one repeatable local rehearsal covering a short synthetic load sample,
  one dependency outage/recovery, restart/compatible rollback and PostgreSQL
  backup/restore into a new disposable target. Reuse existing tests and runbooks.
- Phase 64: focused secret/security and honest-claims review, current mandatory
  scan evidence, a small synthetic screenshot set and one concise demo script.
  Keep known monitoring vulnerabilities deferred; do not restart custom rebuilds.
- Phase 65: one practical AWS dev/demo setup checklist, current cost estimate,
  explicit missing inputs, deployment/rollback steps and a gated cleanup plan.
- Phase 66: one approved AWS dev/demo deployment and bounded operational evidence.
  No second staging environment or separate production deployment is required.
  Public access and real DNS/TLS still need their existing explicit approval.
- Phases 67 and 68 are **Skipped by owner scope decision**, retained as optional
  future work. Preserve existing staging/prod Terraform, Helm and workflow code
  with applicable static checks; label it untested in AWS unless evidence exists.
  Do not re-enable these phases automatically or claim they were completed.
- After approved Phase 66 completion, the next required phase is 69, which retains
  its separate publication/license approval. Required-scope completion excludes
  owner-skipped optional phases, but never excludes the unresolved Phase 62 gate.

All existing authentication, least-privilege, secret, vulnerability, integration
and CI requirements remain. This is a scope reduction, not deployment approval or
permission to weaken checks. The Phase 62 deferral and Phase 66 approval boundary
above still apply. A prepared launch package can remain blocked.

### Efficient autonomous execution

#### Owner-approved CI cost policy (2026-09-16)

- Account-wide GitHub Actions overage is authorized within a USD 5/month budget
  with Stop usage enabled and alerts at 75%, 90% and 100%. Verify billing setup
  before triggering paid CI. Never automatically increase this budget, upgrade
  runners/plans, add paid cache capacity or change other product budgets.
- GitHub billing is the source of actual spend and enforcement; repository rules
  cannot enforce an account invoice cap. Taxes, exchange rates and accrued usage
  may affect invoices. Record runner-minute/artifact-size estimates during reviews.
- Keep large tested images in private GHCR and small required reports in Actions
  for 14 days. Do not migrate reports to a custom registry transport to avoid a
  small approved storage charge. Preserve full provenance and security checks.
- Use focused local checks and existing caches during development; run mandatory
  exact-revision CI on each candidate/fix. Investigate failures before retries;
  unchanged quota failures do not justify repeated reruns. Never count partial
  attempts or cancelled/skipped required checks as release success.
- CI jobs have explicit timeouts at most 30 minutes; preserve stricter limits and
  use five minutes for eligibility. Cancel only superseded runs of the same PR;
  main runs stay independent to preserve each commit's required evidence.
- Develop locally. A future bounded AWS demonstration and cleanup require their
  separate approvals; the GitHub budget does not authorize cloud spending.

Continue to the next phase automatically after completion and review. Do not pause
after a phase or an investigation checkpoint unless a listed approval gate or
concrete blocker applies.

- Audit candidate dependencies and immutable image digests before building new
  integrations around them. Use focused image scans and compatibility probes to
  reject unsuitable candidates early; keep the vulnerability and secret policy.
- During implementation, run the smallest relevant checks that can catch the
  change's failure modes. Run the full required suite on the phase candidate and
  preserve all exact-revision CI/release evidence requirements. Follow-up fixes
  receive relevant local checks and all mandatory CI gates; skipped integration
  tests never count as success.
- Reuse Docker build layers and existing verified tool/dependency caches. Caches
  are performance aids, never substitutes for tests, fresh security audits,
  immutable artifact verification or successful current-revision release gates.
- Reassess a slow investigation at roughly 20-30 minute checkpoints. Record what
  was learned, which options were ruled out, and the next bounded experiment;
  continue independent work without routine permission requests. Do not rerun
  unchanged successful checks without a changed input or unresolved concern.
- A failed candidate or first approach is a finding to remediate, not by itself
  a stop condition. Investigate supported updates, minimal variants, removal of
  unused components, and reproducible targeted patches with compatibility tests.
  Stop only when safe alternatives are exhausted or an existing gate applies.

Keep each implementation within its current phase and retain separate commits
for actionable post-commit findings. These efficiency rules do not authorize
scanner exceptions, weaker security checks, cloud changes, paid resources,
production, real secret changes, or DNS/TLS changes.

## Stop conditions and human approval gates

Stop and request human approval before any action that could create cost, downtime, data loss, credential exposure, or production impact.

Codex must stop before:

- Running `terraform apply`.
- Running `terraform destroy`.
- Creating paid cloud resources.
- Modifying real AWS infrastructure.
- Deploying to production.
- Deleting cloud resources.
- Deleting databases, buckets, registries, clusters, namespaces, or secrets.
- Rotating or changing real secrets.
- Changing DNS or TLS for a real domain.
- Running destructive database migrations.
- Force-pushing shared branches.
- Disabling security checks.
- Bypassing CI/CD approval gates.
- Bypassing branch protection to push to `main`.
- Exposing credentials in logs, commits, or workflow output.

For infrastructure phases, Codex may still safely:

- Write Terraform code.
- Write Kubernetes manifests.
- Write Helm charts.
- Write GitHub Actions workflows.
- Run `terraform fmt`.
- Run `terraform validate`.
- Run `helm lint`.
- Run `helm template`.
- Run unit tests.
- Run static checks.
- Build local Docker images.
- Update documentation.
- Commit and push code to `main` when branch protection and required checks allow it.

If direct push to `main` is blocked by branch protection, missing permissions, failing required checks, or repository policy, stop and report the blocker. Do not bypass protections or force-push.

## Loop completion

The autonomous loop ends only when:

- All phases are marked `Completed`.
- A stop condition requires human approval.
- A blocker prevents safe progress.
- Validation fails and Codex cannot fix it safely.
- Required credentials/access are missing.
- Direct push to `main` is blocked by branch protection, missing permissions, required checks, or repository policy.
- Proceeding would violate the current phase scope.

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

## Phase review and post-commit review format

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

### Post-Commit Review
- Pushed commit:
- Top findings:
- Fix commits:

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
- Commit is pushed to `main`.
- Pushed commit is reviewed and top findings are fixed in separate follow-up commits.
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
