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

NetworkPolicies, External Secrets, workload IAM annotations, HPA, and PDB are later hardening phases.

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
