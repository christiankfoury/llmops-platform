# Repository engineering guide

Production AI Platform is an operations-focused Java LLM gateway and usage dashboard.
Proofbase owns RAG; AgentOps owns workflow execution. Integrations here carry operational
metadata only: never prompts, generated content, tool payloads or customer documents.

## Current state and scope

Read [project scope](PROJECT_SPEC.md), [roadmap](phases.md), [progress](phases-progress.md)
and [maintainer handoff](docs/next-chat-handoff.md) before implementation.
Java 21/Spring Boot in `apps/api-java` is the default runtime. `apps/api` remains the
Python compatibility reference. Flyway is the only active migration owner.

The owner approved source publication preparation before AWS on 2026-09-17. This
supersedes the old requirement to finish AWS before sharing source. It does not
complete Phase 69's cloud closeout or authorize a deployable monitoring release.
Finish the reviewable cleanup, then stop for final repository visibility approval.

- Phase 62 stays **Blocked**. Preserve both dirty local working trees and parked
  custom rebuild experiments. Do not stage them wholesale, resume remediation,
  suppress findings or adopt their images. Keep the [monitoring backlog](docs/security/monitoring-vulnerability-backlog.md).
- Phases 63–65 completed local resilience, security/demo and AWS preparation.
- Phase 66 requires monitoring completion, current CI, AWS setup and explicit
  deployment/cost approval. One bounded dev/demo environment is the target.
- Phases 67–68 remain skipped. Preserve their static configuration without live claims.
- Public application access, real DNS/TLS and cleanup retain separate approvals.

## Change and review workflow

1. Inspect status and work from an isolated `codex/` branch when unrelated work exists.
2. Plan a bounded change, implement it and update affected documentation.
3. Run focused checks locally, preserving meaningful security and integration tests.
4. Commit conventionally with Summary, Validation, Security and Phase/scope notes.
5. Open a pull request to `main`. Require every applicable CI job to pass on the
   current revision; merge through branch protection, without an administrative bypass.
6. Verify the merged main revision's full CI and exact-revision release evidence.
   PR checks do not replace main's immutable package provenance.
7. Review the result. Put actionable follow-up fixes in separate commits/PRs,
   validate them, and update progress and evidence. No routine approval is needed
   for authorized code, documentation or local checks.

The owner selected required PRs/checks with no second reviewer requirement for this
solo repository. This replaces the historical direct-push phase loop. Do not force
push shared branches or turn off protections to unblock work.

## Validation and cost

- Java: Maven verification, formatting/static checks and real PostgreSQL/Redis tests.
  Skipped required database tests are not passes. Frontend: lint, types, tests, build.
- Docker changes: build and scan. Terraform: format/validate. Helm/Kubernetes:
  lint, render and schema/policy checks. Workflow changes: actionlint and policy tests.
- Use caches and focused local checks. Keep fresh mandatory scans, verified digests,
  exact-revision eligibility, and 14-day Actions evidence. Images stay in private GHCR.
- GitHub Actions overage is authorized within the account's **USD 5/month** budget,
  with Stop usage and 75/90/100% alerts. Verify saved billing settings before billable
  runs. GitHub billing enforces spend; repository configuration cannot cap an invoice.
- Keep 30-minute job ceilings, stricter existing limits and five-minute eligibility.
  Cancel only superseded PR runs; main runs retain independent commit evidence.
- Diagnose failures before retries. No automatic budget increases, paid cache capacity,
  larger runners, subscription changes or recurring billing workflows. Record runner
  minutes/artifact size when reviewing CI. Taxes/accrued usage may affect invoices.

## Security and operational boundaries

Never commit secrets. Use placeholder-only examples; keep real environment files,
state, dumps and credentials outside Git. Never print tokens or provider payloads.
Preserve least privilege, project authorization, CSRF/session boundaries, loopback
local ports, private management metrics, non-root containers and resource limits.
Caches, historical scans and documented vulnerabilities never waive security checks.
No scanner exceptions or automatic destructive schema updates are authorized.

Obtain explicit approval before AWS apply/destroy or other real infrastructure
changes, paid cloud resources, production/public deployments, deleting databases,
volumes, buckets, registries, clusters, namespaces or secrets, secret rotation,
real DNS/TLS changes, destructive migrations or publication. Stop if credentials,
required checks or policy prevent safe progress; report the concrete blocker.
The Actions budget authorizes only its stated CI spending, not AWS or providers.

## Historical reference

[Archived implementation criteria](docs/archive/phase-criteria.md),
[phase history](docs/archive/phase-history.md) and [technical reviews](docs/archive/phase-reviews)
retain earlier decisions and evidence. Historical instructions do not override this
file or current owner direction. Keep measured local results distinct from synthetic
UI examples, static infrastructure validation and future AWS evidence.
