## Phase 58 Review

### Summary
- Switched default local and Kubernetes packaging to Java, with a separate Flyway image and explicit local Python reference.
- Added hosted JDBC TLS enforcement, private management Service/policy, bounded JVM resources and writable paths, and fresh container/TLS CI acceptance.
- Status: implementation pushed for CI and review; phase completion waits for actual container evidence.

### Scope Check
- In scope: Java image/runtime cutover, migration/seed ordering, data TLS, probes/resources/shutdown, Kubernetes settings/secrets, container and manifest checks.
- Out of scope avoided: real AWS resources, identity/secret changes, deployed Kubernetes/monitoring, immutable release redesign and public visibility.

### Files Changed
- Java Dockerfile/probe, transport/seed configuration and tests; Node 24 web image; default/reference/TLS Compose, scripts, Makefile and examples.
- Helm and raw Kubernetes runtime configuration, separate metrics service/policy, runtime/migration/session secret boundaries, optional migration Job.
- CI image/runtime checks, deployment cutover holds, README/cutover/local/deployment/migration/runbook and phase progress.

### Validation
- Command: Maven Wrapper strict-checksum spotless:apply clean verify.
- Result: 277 tests passed without failures/errors/skips; both runnable JARs packaged.
- Command: exact packaged CI migration, seed-local and application smoke against isolated PostgreSQL/Redis.
- Result: health, gateway, both clients/replays, signed operator, bounded bodies, private metrics and redacted correlated logs passed.
- Command: scripts/validate_java_manifests.py with Helm 3.18.4 and kubectl kustomize.
- Result: strict lint/render and runtime/network/secret boundary checks pass for base/dev/staging/prod, optional OIDC/migration Job, and refusal of unprotected metrics.
- Command: Compose config (base/TLS), Ruff checks for three fixture/validation scripts, direct Java 21 probe compilation, workflow/embedded Python parse and wrapper digest validation.
- Result: passed. Linux Docker engine is unavailable locally; actual image/fresh TLS stack results must come from CI. General Kubernetes/CRD schema validation expands in Phase 59.
- CI: pending pushed-run evidence.

### Security Review
- Secrets: only placeholders and ignored generated fixture keys; separate runtime, migration-owner and web session references; public trust bundle references.
- Auth: hosted operator/web modes default closed, Compose uses isolated synthetic web fixtures; packaged signed operator checks remain required.
- IAM/RBAC: no cloud changes; migration has no service-account token. Privileged bootstrap separation is Phase 59.
- Network: hosted JDBC verify-full and Redis TLS/password; management port is private and policy-restricted, public paths excluded. No host-published management port.
- Supply chain: pinned Temurin/Node/PostgreSQL/Redis bases, strict Maven wrapper/checksums and all three image vulnerability gates. Expanded Java SBOM/eligibility is Phase 60.

### Reliability Review
- Health checks: bounded startup probe, dependency-aware readiness and independent liveness; read-only images with explicitly bounded writable mounts.
- Rollback: new local volume preserves Python data; explicit schema adoption only, no automatic DDL/downgrade. Old cloud deployment/rollback jobs are held until Phase 61.
- Failure handling: 1 GiB JVM container/512 MiB heap, 60-second termination allowance, migration deadline/no retries and readiness failure on bad TLS.

### Observability Review
- Logs: existing Java allowlisted structured logs; synthetic test fixture logs only.
- Metrics: distinct ClusterIP service on 9080 with both namespace and Prometheus pod selectors; no identifiers in labels.
- Traces: environment-specific bounded HTTPS exporter settings; no real collector called.
- Dashboards: isolated local fixtures; signed OIDC/project setup required for real data; runnable monitoring remains Phase 62.

### Risks / Follow-ups
- Container runtime/TLS acceptance awaits CI; static manifests do not prove a running EKS policy or pod lifecycle.
- AWS public trust, runtime/owner roles, identity, SecretStore/bootstrap and paid deployment remain later approved work.
- Local Redis image is verified Linux amd64; ARM and performance sizing are not claimed.
- Historical deployment/browser docs retain clearly marked Python context; Java cutover guide is authoritative.

### Post-Commit Review
- Pushed commit: 7d9bb448f0fc36ccb17c662abbdcd6c808b6d832.
- Top findings: Kubernetes web configuration omitted the required OIDC audience; minimal JDK image lacked unzip and caused Maven Wrapper to select a tarball against the pinned ZIP checksum. Both have separate fixes (eff07cc and 38962cc). Review also added an actual PID 1/SIGTERM check to cover the shipped entrypoint, beyond Java lifecycle and static grace-period tests; required CI remains pending.
- Fix commits: separate OIDC audience wiring and Maven archive extraction fixes; final identifiers/CI evidence follow.

### Next Phase
- Phase 59: AWS infrastructure validation and bootstrap boundaries, after Phase 58 checks/review pass.
