# Java Spring Boot conversion and AWS public release

Decision date: 2026-09-06. Status: Active roadmap; implementation begins with Phase 49 after the Phase 48 planning commit is pushed and reviewed.

## Approved direction

The user selected Java Spring Boot and retained AWS. EKS, ECR, RDS PostgreSQL, ElastiCache Redis, Secrets Manager, Terraform, Helm, GitHub Actions, and the Next.js frontend remain the platform direction. The earlier Azure proposal is superseded and is not an active migration.

Phases 1-47 are the historical Python/infrastructure baseline. Their completion does not assert that Java is implemented or AWS resources are running. New phases 48-69 distinguish implementation, local validation, cloud validation, and publication.

## Implementation design

- Use Java 21, Spring Boot MVC, Maven Wrapper, Jakarta Validation, Spring Data JPA/Hibernate, PostgreSQL, and Flyway. Pin the supported Spring Boot patch and build tooling in Phase 50 after checking available artifacts. Java 21 is installed locally; Spring documents supported Java/build combinations in its [system requirements](https://docs.spring.io/spring-boot/system-requirements.html).
- Build the replacement in `apps/api-java` while `apps/api` remains the local reference. Switch the runtime only in Phase 58 after contracts and authorization pass. Keep the Python implementation available for regression comparison until it can be removed safely.
- Keep the HTTP paths and compatible JSON contracts used by Next.js, Proofbase, and AgentOps. Document intentional changes for authentication, safe validation responses, and bounded limits rather than preserving insecure behavior.
- Port DTO validation explicitly: unknown telemetry fields, sensitive metadata, numeric bounds, timezone-aware timestamps, aliases, and decimal strings are part of the contract. Use BigDecimal for cost and preserve six-decimal storage/rounding behavior.
- Preserve PostgreSQL tables, IDs, relationships, uniqueness and JSONB data. Flyway becomes the sole migration owner after an explicit schema-verification/adoption step. Never enable Hibernate automatic schema updates or blind Flyway baselining against an existing database. Test fresh installation and an Alembic-created database copy. Spring supports [Flyway integration](https://docs.spring.io/spring-boot/how-to/data-initialization.html).
- Keep machine application keys distinct from operator identities. Add OIDC authorization, verified audit actors, viewer/operator permissions and server-side project grants. Use local identity fixtures/provider tooling for tests; select real identity-provider settings only at launch preflight. Do not expose the Python baseline or unfinished Java operator APIs publicly.
- Introduce atomic Redis limits and explicit outage behavior, real dependency readiness, safe liveness, graceful shutdown, and bounded retries. Redis integration must use TLS in the AWS configuration.
- Instrument with Actuator, Micrometer and OpenTelemetry; preserve metric compatibility or update dashboards atomically. Keep identities/request IDs out of metric labels. Spring describes the [observation API](https://docs.spring.io/spring-boot/reference/actuator/observability.html).
- Retain Helm packaging and AWS service definitions. Separate privileged cluster bootstrap from namespace release permissions, solve private EKS runner connectivity, and promote scanned images by digest from a successful exact-revision CI run.
- Phase 59 design (2026-09-07): initial pinned v3.5.0 compatibility passed before adoption of Terraform-owned ALB/listeners/rules/security groups/target groups plus restricted TargetGroupBinding reconciliation. Actual bootstrap templates and IAM policy now receive lifecycle, readiness, restart/outage, RBAC and admission regression tests. Ingress remains read-only because its reconciler cannot be switched off; native admission forbids Ingress creation. No scanner exception is approved or active. [Design and evidence](targetgroupbinding-design.md); live AWS IAM/data-plane validation remains approval-gated.
- Phase 61 release ownership: CI builds/scans once and verifies OCI digest preservation before adoption. Manual preflight verifies current-policy artifacts and staged receipts; distinct publisher/migration/application OIDC roles remain hard-held until environment approval. Rollback uses a read-only live-schema verifier and never downgrades data. See [release procedure](immutable-release-runbook.md).
- Deploy a working monitoring stack and replace Promtail with Alloy. Capture measured local evidence first and cloud evidence only after approved deployment.
- Phase 62 currently has passing local runtime evidence but is held by failed upstream monitoring image audits (2026-09-07). The prototype remains uncommitted and uninstalled; all image, transport/storage and required CI gates must pass before completion. See [the Phase 62 validation hold](phase-reviews/phase-62.md). No scanner exception or cloud approval was activated.
- Keep paid provider integration optional. The mock gateway and synthetic client events support this DevOps demonstration. Azure conversion, advanced RAG, workflow orchestration, automatic secret rotation, and multi-region expansion are outside this release scope.

## Phase sequence

| Phase | Outcome |
|---:|---|
| 48 | Java conversion and AWS release roadmap |
| 49 | Backend compatibility contract baseline |
| 50 | Spring Boot build and service foundation |
| 51 | PostgreSQL persistence and migration handover |
| 52 | Java gateway and model routing |
| 53 | Java Proofbase and AgentOps telemetry ingestion |
| 54 | Java usage and operator configuration APIs |
| 55 | Operator authorization and application key lifecycle |
| 56 | Distributed limits and dependency-aware readiness |
| 57 | Java metrics logs and traces |
| 58 | Java Docker Compose and Helm runtime cutover |
| 59 | AWS infrastructure validation and bootstrap boundaries |
| 60 | Java supply chain and CI release eligibility |
| 61 | AWS immutable promotion migrations and rollback |
| 62 | Runnable monitoring stack and supported log collection |
| 63 | Local resilience recovery and cost rehearsal |
| 64 | Public repository and isolated demo preparation |
| 65 | AWS launch preflight and approval package |
| 66 | Approved AWS dev deployment and operational evidence |
| 67 | Approved staging promotion and recovery exercise |
| 68 | Approved production or public demo launch |
| 69 | Approved public repository release and closeout |

Detailed deliverables and acceptance criteria are authoritative in [phases.md](../phases.md); execution status is in [phases-progress.md](../phases-progress.md).

## Execution and review

For each phase: reread AGENTS.md/spec/roadmap/progress; write the implementation plan; implement only that phase; run relevant checks and fix issues; update evidence and progress; create a detailed conventional commit; push main without bypassing protections; review the pushed diff; fix each top finding in a separate validated/pushed commit; record the prescribed phase review; advance automatically until a genuine blocker or approval gate.

Java checks use Maven verification, formatting/static analysis and unit/integration/contract tests. Database/Redis tests must run against real disposable services in required CI, not silently skip. Frontend checks, Docker builds/scans, Terraform fmt/validate, all-environment Helm rendering and CRD-aware schema validation remain required when affected. GitHub readback verifies the pushed SHA and CI status. Review records live in `docs/phase-reviews/`.

## Gates and cost boundaries

Code, local tests, local Docker, static infrastructure validation and ordinary commits/pushes are authorized. AWS resource creation/change, terraform apply/destroy, production deployment, real secret changes, destructive migrations, and real-domain DNS/TLS changes retain the explicit gates in AGENTS.md. Prepare a concrete reviewed change/cost package before asking for the final approval.

Repository publication and licensing are separate final decisions. Prepare the full-history secret review and sanitized assets first; do not infer authorization to change visibility from a request to implement the roadmap. Do not fabricate screenshots, successful deploys, or tested recovery targets.

A missing local tool should be resolved using a pinned/verifiable workspace tool or local Docker where practical. A blocked required check is recorded accurately; no skipped integration test counts as successful validation. If protected main rejects a push, stop without bypassing it.

## Definition of success

A clean checkout can build and run the Java API and dashboard, securely receive gateway/Proofbase/AgentOps requests, and deploy through reproducible AWS workflows. The portfolio shows a verified change moving through CI, identity, deployment, telemetry, an actionable alert, rollback, and tested recovery, with real costs and validation limitations visible.
