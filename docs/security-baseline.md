# Security Baseline

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

## Container security

Target controls:

- non-root user
- minimal runtime image
- dependency scanning
- image scanning
- no package manager cache in final image
- no secrets baked into image
- explicit health checks

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

NetworkPolicies, HPA, and PDB are later hardening phases.

Phase 15 keeps the same secret-reference and non-root workload posture in Helm templates. The chart does not render Kubernetes Secret values.

Phase 24 adds External Secrets integration:

- Runtime Kubernetes Secrets are generated from AWS Secrets Manager.
- External Secrets Operator uses an IRSA role scoped to the environment's Secrets Manager ARNs.
- Terraform creates secret containers and IAM policy only; it does not write secret values to state.
- Secret names and properties are documented in `docs/secrets-management.md`.

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
