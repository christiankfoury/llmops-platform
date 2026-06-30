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
