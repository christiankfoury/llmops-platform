> Historical document. See the [current documentation](../README.md).

# Security Baseline

Current AWS load-balancing ownership is defined in [the TargetGroupBinding design](../targetgroupbinding-design.md): Terraform owns ALB/listeners/rules/security groups/target groups; the pinned controller has no Ingress writes and only exact-group registration permissions. Bootstrap controls immutable bindings and readiness admission. Historical Ingress examples below do not supersede this approval-gated sequence.

## Current Java and release posture (2026-09-08)

The [focused Phase 64 review](../security/phase-64-review.md) and
[Java operator security](../java-operator-security.md) describe the current runtime.
Java is the default after Phase 58, Flyway is sole migration owner, and Redis
provides atomic distributed limits. Unconfigured operator endpoints are closed;
OIDC identities receive only explicit database-backed project grants. The default
web demo serves fixed synthetic fixtures and rejects all writes.

Release jobs are manual and held, with separate publisher/migration/application
identities and explicit environment approval checks. No AWS deployment exists.
The sections labeled Phase 11–26 below retain historical design context; their
in-process/Python/automatic-deploy descriptions are superseded by the current Java
and immutable-release documents. Monitoring vulnerabilities remain deferred and
Phase 62 is a launch/publication blocker. Recording a risk is never permission to
weaken checks; the scanner exception remains inactive.

## Core rules

- Never commit secrets.
- Never log secrets.
- Never store API keys in plaintext.
- Use `.env.example`, not real `.env` files.
- Use External Secrets or cloud secrets for Kubernetes.
- Use least-privilege IAM.
- Use environment isolation.
- Scan dependencies and images in CI.

## API security

Required controls:

- API key authentication
- hashed API key storage
- key active/inactive status
- rate limiting
- audit logs for sensitive changes
- no raw provider credentials in logs
- request IDs for traceability

Phase 25 API controls:

- Gateway requests pass through a fixed-window rate limiter before database authentication.
- The limiter is keyed by the SHA-256 hash of the supplied API key so plaintext API keys are not stored in rate-limit state.
- Local and Kubernetes defaults allow 60 requests per 60-second window.
- The in-process limiter is bounded to 10,000 identifiers to avoid unbounded memory growth from unique-key spray.
- Rejections return HTTP 429 and increment `llm_gateway_rate_limit_rejections_total`.
- This is a single-process portfolio baseline; Redis-backed distributed rate limiting is the production extension path when multiple replicas need a shared counter.

## Container security

Implemented controls:

- non-root user
- minimal runtime image
- dependency scanning
- image scanning
- no package manager cache in final image
- no secrets baked into image
- explicit health checks
- read-only root filesystem in Kubernetes
- dropped Linux capabilities in Kubernetes
- no privilege escalation in Kubernetes

## Kubernetes security

Target controls:

- service accounts per workload
- resource requests and limits
- security contexts
- NetworkPolicies
- ExternalSecrets
- restricted ingress
- least-privilege workload identity

Phase 14 baseline controls:

- API and web workloads run with dedicated service accounts.
- Service account token automounting is disabled for both workloads.
- Pods require non-root containers and use the runtime default seccomp profile.
- Containers drop all Linux capabilities and disable privilege escalation.
- Deployments include CPU/memory requests and limits.
- Runtime database and Redis connection strings are referenced from a Kubernetes Secret and are not committed.

NetworkPolicies, HPA, and PDB are included in later Kubernetes and Helm deployment paths.

Phase 15 keeps the same secret-reference and non-root workload posture in Helm templates. The chart does not render Kubernetes Secret values.

Phase 24 adds External Secrets integration:

- Runtime Kubernetes Secrets are generated from AWS Secrets Manager.
- External Secrets Operator uses an IRSA role scoped to the environment's Secrets Manager ARNs.
- Terraform creates secret containers and IAM policy only; it does not write secret values to state.
- Secret names and properties are documented in `docs/secrets-management.md`.

Phase 25 adds NetworkPolicies and confirms least-privilege service-account behavior:

- API and web pods are covered by a namespace default-deny ingress policy.
- API pods allow port `8000` only from web pods and configured private ingress CIDRs.
- Web pods allow port `3000` only from configured private ingress CIDRs.
- Pod egress remains open in Phase 25 because DNS, RDS, Redis, OpenTelemetry, and provider egress paths are environment-specific.
- API and web service accounts still have `automountServiceAccountToken: false`.
- No workload RBAC permissions are granted because the app does not call the Kubernetes API.
- Helm exposes the private ingress CIDR list through `networkPolicy.ingressCidrs`.
- Terraform EKS clusters use KMS envelope encryption for Kubernetes Secrets.
- Dev, staging, and prod EKS API endpoints default to private-only access.
- RDS PostgreSQL and ElastiCache Redis security groups allow inbound traffic only from approved platform security groups and do not declare public egress.

Phase 26 adds availability controls:

- API and web workloads have HorizontalPodAutoscalers with bounded replica limits.
- API and web workloads have PodDisruptionBudgets to preserve availability during voluntary disruption.
- Graceful termination settings give load balancers and readiness checks time to drain pods during rollouts.

## Supply-chain security

Phase 25 blocking CI gates:

- Python production dependencies are audited with `pip-audit --strict` and no longer run with `continue-on-error`.
- API and web images are built and scanned with Trivy for high/critical findings.
- A repository-level Trivy filesystem scan checks dependencies, IaC/config, and secret patterns for high/critical findings.
- Frontend dependencies continue to use `npm audit --audit-level=high`.

Any CI finding that requires accepting risk should be documented in this file or a linked security exception before the gate is relaxed.

## Audit log review

See `docs/security-audit.md` for safe audit log review queries, redaction guidance, and escalation criteria.

## Terraform security

Target controls:

- no committed credentials
- environment-specific variables
- remote state documented
- state encryption documented
- least-privilege IAM
- private database subnets
- explicit security groups
- backups for non-dev data services

Phase 11 foundation controls:

- AWS provider credentials are not committed and are expected through the standard provider chain.
- Environment roots are separate for dev, staging, and prod.
- `backend.hcl.example` files document encrypted S3 state and DynamoDB locking placeholders without real bucket or table names.
- Secrets Manager resources are placeholders only; secret values are not written to Terraform state.
- The optional GitHub Actions OIDC role is disabled by default and scoped to repository, branch/environment, and ECR repository ARNs when enabled.
- `ecr:GetAuthorizationToken` uses resource `"*"` because AWS requires it; ECR publish actions are scoped to repository ARNs.
- EKS workload identity is prepared through an environment-specific OIDC provider so later Kubernetes service accounts can use scoped IAM roles instead of node-wide credentials.
- RDS and Redis security groups accept traffic only from the EKS cluster security group.
- RDS storage is encrypted and the master password is generated and managed by AWS rather than committed or stored in Terraform variables.
- Redis is encrypted at rest and in transit.

Phase 16 dev deployment controls:

- GitHub Actions uses OIDC role assumption instead of committed AWS keys.
- Dev image publishing is scoped to the Terraform-created ECR repositories.
- The deploy role can describe the dev EKS cluster for kubeconfig generation.
- Kubernetes release permissions are scoped to `ai-platform-dev` through an EKS access entry using `AmazonEKSEditPolicy`.
- Automatic dev deploys require explicit repository variables before a push to `main` can mutate the dev cluster.
- Runtime database and Redis connection strings remain Kubernetes secret references and are not committed or printed by the workflow.

Phase 17 release controls:

- Staging and production deployment workflows are manual only.
- Production uses the protected GitHub `prod` Environment as the approval gate.
- Production also requires an explicit `deploy-prod` confirmation input.
- Staging and production deploy roles use OIDC and namespace-scoped EKS access entries.
- Release notes are captured in the GitHub Actions job summary.
- No static cloud credentials, kubeconfigs, or runtime secret values are committed.

Phase 18 rollback controls:

- Rollbacks are manual-only and require a selected Helm revision.
- Production rollback uses the protected GitHub `prod` Environment approval gate.
- Production rollback also requires an explicit `rollback-prod` confirmation input.
- Rollback uses existing OIDC deploy roles and namespace-scoped Kubernetes access.
- Rollback workflow output records release, namespace, revision, reason, and follow-up steps without printing secret values.

## Logging policy

Do log:

- request ID
- trace ID
- route
- status
- latency
- error category
- model/provider name
- estimated token/cost data

Do not log:

- API key values
- provider secrets
- database passwords
- raw authorization headers
- sensitive prompts by default
- personally identifiable information unless explicitly required and protected

## External telemetry data policy

External client-app telemetry must follow [external-telemetry-contract.md](../external-telemetry-contract.md).

Proofbase telemetry may include operational fields such as model, provider, token counts, estimated cost, latency, status, error category, prompt version, source project IDs, and bounded metadata. It must not include API keys, provider credentials, full prompts, full questions, rewritten questions, retrieved chunks, citation text, uploaded document text, extracted Markdown, cleaned Markdown, provider payloads, or raw customer data by default.

AgentOps telemetry may include operational fields such as workflow ID, agent-step ID, agent name/type, step order, retry count, model, provider, token counts, estimated cost, latency, status, safe error category, prompt version identifier, workflow status, step status, and response type. It must not include API keys, provider credentials, prompt text, system instructions, generated outputs, structured response JSON, workflow input/output JSON, tool arguments, tool results, provider payloads, or user/customer data by default.

Duplicate telemetry events should be suppressed by stable event IDs so retries cannot inflate cost or request totals.

Telemetry API keys:

- Treat client telemetry keys like gateway API keys: store only hashed values in the platform and keep plaintext values in local `.env` files, CI/CD secrets, or cloud secret managers.
- Do not print telemetry keys in client logs, platform logs, browser screenshots, GitHub Actions summaries, or runbooks.
- Rotate a client telemetry key if it appears in logs, screenshots, shell history, or committed files.

Proofbase redaction boundary:

- Production AI Platform may claim centralized Proofbase telemetry, usage, latency, error, token, and estimated-cost visibility.
- It must not claim to perform Proofbase retrieval, citation validation, permission filtering, memory safety checks, document ingestion, or benchmark evaluation.

AgentOps redaction boundary:

- Production AI Platform may claim centralized AgentOps workflow and agent-step telemetry, usage, latency, status, retry, token, error, and estimated-cost visibility.
- It must not claim to execute AgentOps workflows, own AgentOps prompts, inspect generated outputs, evaluate workflow quality, run tools, or handle tool payloads.
- Workflow summary events must remain aggregate-only and non-billable in the platform to avoid double-counting per-step cost.

- Screenshots should show aggregate operational data, short request ids, source app, operation type, model, latency, and estimated cost only.

## Java operator boundary (Phase 55)

The Java service replaces local operator identity with RS256 OIDC verification and explicit viewer/operator project grants. The dashboard uses a server-side OIDC code flow, encrypted HttpOnly sessions and origin/CSRF checks; machine keys remain separate. Application keys are generated with 256 bits of entropy, returned once, stored hashed and revoked with atomic verified audit records. Default access is closed. The explicit frontend synthetic demo never queries platform data. See [Java operator security](../java-operator-security.md) for exact settings, tests and stateless-session revocation limits. These controls apply to Java; the historical Python deployment remains a reference until Phase 58.

## Java bounded admission (Phase 56)

The Java service now bounds unauthenticated traffic with three fixed Redis counters, trusted-key quotas, in-flight requests, headers, paths, queries, body sizes and read deadlines. Hosted Redis requires authenticated TLS with certificate verification. Dependency loss fails closed; API errors omit credentials and diagnostic text. These admission controls do not replace ingress abuse controls or guarantee spending limits. See [Java reliability](../java-reliability.md).

## Java observability boundary (Phase 57)

Actuator health/Prometheus run on a separate loopback management listener; detailed diagnostics stay disabled. Operational logs use a strict field allowlist and omit raw framework errors, payloads, arguments and arbitrary MDC. Traces omit content, SQL, exceptions and baggage, and use bounded sampling/export queues. Hosted collectors require HTTPS. Network access to a non-loopback monitoring port must be explicitly restricted during deployment. See [Java observability](../java-observability.md).
