# Engineering guide

LLMOps Platform provides a Java LLM gateway and operational telemetry dashboard.
Read the [project scope](PROJECT_SPEC.md), [roadmap](phases.md),
[progress](phases-progress.md) and [contribution guide](CONTRIBUTING.md) before changes.

## Architecture boundaries

- Java 21/Spring Boot in `apps/api-java` is the default runtime. `apps/api` is the
  Python compatibility reference. Flyway is the sole active migration owner.
- Proofbase owns RAG; AgentOps owns workflows. Telemetry carries operational
  metadata only, never prompts, generated content, tool payloads or customer documents.
- The default dashboard uses isolated sample data. Authenticated usage requires
  OIDC and project grants. Never fall back to demo access after authentication fails.
- Monitoring remains [blocked](docs/security/monitoring-vulnerability-backlog.md).
  Preserve unfinished local work; do not adopt prototype images, resume deferred
  rebuilds or introduce scanner exceptions as part of unrelated changes.
- AWS is not deployed. Phases 63–65 have local/preparation evidence; Phase 66 needs
  monitoring eligibility and explicit deployment approval. Phases 67–68 stay skipped.
  Source publication does not complete the monitoring or cloud milestones.

## Changes and validation

1. Inspect Git status. Use an isolated `codex/` branch if unrelated work exists;
   never reset, discard or stage another worktree's unfinished changes.
2. Keep the change bounded, update affected documentation and test relevant failure modes.
3. Commit conventionally with summary, validation, security and scope notes.
4. Open a PR to `main`; require up-to-date checks and resolve review findings.
   Merge through branch protection without bypass, force push or branch deletion.
5. Verify merged-main CI and exact-revision release evidence. PR results and older
   successful runs do not establish the merged revision's immutable provenance.
6. Fix actionable review findings in separate commits/PRs and verify them again.

Java changes require Maven verification, formatting/static checks and real PostgreSQL/
Redis tests; skipped required tests are not passes. Frontend changes require lint,
types, tests and build. Docker changes require build/scan; infrastructure changes
require Terraform validation, Helm rendering and Kubernetes schema/policy checks.
Workflow changes require actionlint and CI-policy tests. See [testing](docs/testing.md).

Use verified caches and focused local checks, retaining all mandatory CI scans,
14-day evidence, immutable digest verification and private image retention.
Respect configured billing limits and job timeouts; verify the approved allowance
before billable runs. Do not raise budgets, runner tiers or cache capacity automatically.
Investigate failures before retrying; only superseded PR runs may be cancelled.

## Security and operational changes

Never commit or print secrets. Use placeholders in examples; keep real environment
files, state, dumps and credentials outside Git. Preserve least privilege, project
authorization, CSRF/session protections, loopback local ports and private metrics.
Never enable automatic destructive schema updates or waive security checks.

AWS apply/destroy, paid resources, public/production deployment, real DNS/TLS,
secret changes, destructive migrations, deletion of databases/volumes/cloud resources,
and repository publication require explicit approval. Stop and report unavailable
credentials, failing required checks or policy blockers; do not bypass protections.

[Archived reviews](docs/archive/README.md) retain dated engineering evidence.
Historical instructions do not override current scope or security boundaries.
