# Decision Log

Use this file to record major architecture decisions.

## ADR-001: Cloud provider

Decision: Use AWS.

Reason:

- Broad market relevance.
- Strong fit for DevOps/cloud roles.
- EKS, ECR, RDS, ElastiCache, IAM, and Secrets Manager map well to the project goals.

Tradeoff:

- AWS can be more complex and costly than local-only or simpler PaaS options.

## ADR-002: Backend framework

Decision: Use FastAPI.

Reason:

- Strong for API development.
- Python fits AI/LLM workflows.
- Easy OpenTelemetry and Prometheus integration.

## ADR-003: Frontend framework

Decision: Use Next.js.

Reason:

- Common in full-stack roles.
- Good dashboard experience.
- Strong TypeScript ecosystem.

## ADR-004: Kubernetes packaging

Decision: Use Helm.

Reason:

- Common in production Kubernetes workflows.
- Supports environment-specific values.
- Works with both GitHub Actions and Argo CD.

## ADR-005: GitOps

Decision: Add Argo CD as a later optional phase.

Reason:

- Keeps the core CI/CD path simpler first.
- Adds advanced platform credibility near the end.
